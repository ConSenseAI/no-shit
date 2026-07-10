#!/usr/bin/env python3
"""noshit-f0-killbill — deterministic end-to-end proof (FIXTURES §2.1 rung 1).

Engine-native clock. A subscription with an 8-day trial is created at virtual
T0; when the Kill Bill TEST CLOCK (not wall time) crosses T0+8d the trial
converts, an invoice is cut, and the default payment method is charged; a
subsequent cancel is honored at the period boundary. The whole thing runs in
minutes because time is moved by the engine, not waited out.

Flow: down -v -> up -> wait healthy -> tenant -> catalog -> account + test
payment method -> subscribe@T0 -> assert $0 trial invoice -> move clock past
T0+8d -> assert conversion invoice + successful charge -> cancel -> move clock
to the period end -> assert entitlement ended -> print the virtual-time timeline
-> tear down (unless --keep). Exits nonzero on any failed assertion.

Reads the clock via clockctl.Clock and the mail sink via the shared
harness/mailsink.py. Stdlib only.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "harness")))

from clockctl import Clock  # noqa: E402

try:
    from mailsink import Mailsink  # shared sink client (platform/harness)
except Exception:  # pragma: no cover - sink is non-critical to the clock proof
    Mailsink = None

PROJECT = "noshit-f0-killbill"
PLAN = "standard-monthly"
TRIAL_DAYS = 8
MONTHLY_PRICE = 29.95
T0 = "2026-01-15T08:00:00"  # fixed virtual origin -> deterministic transcript

# Money charged by the external/test payment plugin for auto-pay.
EXTERNAL_PLUGIN = "__EXTERNAL_PAYMENT__"


# --------------------------------------------------------------------------- #
# env + compose
# --------------------------------------------------------------------------- #
def load_env() -> None:
    """Ensure .env exists (via setup.sh), then load it into os.environ."""
    env_path = os.path.join(HERE, ".env")
    if not os.path.exists(env_path):
        subprocess.run([os.path.join(HERE, "setup.sh")], check=True, cwd=HERE)
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


def sg_compose(*args: str, capture: bool = False) -> subprocess.CompletedProcess:
    """Run `docker compose -p PROJECT ...` under `sg docker` (host quirk)."""
    inner = "docker compose -p " + PROJECT + " " + " ".join(args)
    return subprocess.run(
        ["sg", "docker", "-c", inner],
        cwd=HERE,
        text=True,
        capture_output=capture,
    )


# --------------------------------------------------------------------------- #
# Kill Bill REST client (accounts / catalog / subscriptions / invoices / pay)
# --------------------------------------------------------------------------- #
class KB:
    def __init__(self) -> None:
        port = os.environ.get("KB_API_PORT", "8080")
        self.base = f"http://127.0.0.1:{port}"
        self.user = os.environ.get("KB_ADMIN_USER", "admin")
        self.password = os.environ.get("KB_ADMIN_PASSWORD", "password")
        self.api_key = os.environ.get("KB_TENANT_API_KEY", "noshit-f0")
        self.api_secret = os.environ.get("KB_TENANT_API_SECRET", "")
        self.created_by = "noshit-f0-demo"

    def _headers(self, tenant: bool, mutating: bool, xml: bool) -> dict:
        tok = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
        h = {"Accept": "application/json", "Authorization": "Basic " + tok}
        if tenant:
            h["X-Killbill-ApiKey"] = self.api_key
            h["X-Killbill-ApiSecret"] = self.api_secret
        if mutating:
            h["X-Killbill-CreatedBy"] = self.created_by
            h["Content-Type"] = "text/xml" if xml else "application/json"
        return h

    def req(self, method, path, body=None, params=None, tenant=True, xml=False, timeout=60):
        url = self.base + path
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url += "?" + urllib.parse.urlencode(clean)
        data = None
        mutating = method in ("POST", "PUT", "DELETE")
        if body is not None:
            data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, method=method,
                                     headers=self._headers(tenant, mutating, xml))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode("utf-8")
                loc = r.headers.get("Location")
                parsed = json.loads(raw) if raw.strip() else None
                return r.status, loc, parsed
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            return e.code, None, detail

    # -- typed helpers --
    def create_tenant(self):
        code, _, body = self.req("POST", "/1.0/kb/tenants", tenant=False,
                                 body={"apiKey": self.api_key, "apiSecret": self.api_secret})
        if code not in (201, 409):
            raise RuntimeError(f"create_tenant -> {code}: {body}")
        return code

    def upload_catalog(self, xml_text: str):
        code, _, body = self.req("POST", "/1.0/kb/catalog/xml", body=xml_text, xml=True)
        if code not in (201, 200):
            raise RuntimeError(f"upload_catalog -> {code}: {body}")

    def create_account(self):
        # locale is set so the email-notifications plugin (--with-email) can pick
        # a template; it is harmless for the core clock proof.
        code, loc, _ = self.req("POST", "/1.0/kb/accounts",
                                body={"name": "F0 Demo", "email": "subscriber@fixtures.local",
                                      "currency": "USD", "timeZone": "UTC", "locale": "en_US"})
        if code != 201 or not loc:
            raise RuntimeError(f"create_account -> {code}")
        return loc.rsplit("/", 1)[-1]

    def upload_email_config(self, text: str) -> int:
        """POST the per-tenant email-notifications config (text/plain body)."""
        tok = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
        headers = {"Authorization": "Basic " + tok, "Accept": "application/json",
                   "X-Killbill-ApiKey": self.api_key, "X-Killbill-ApiSecret": self.api_secret,
                   "X-Killbill-CreatedBy": self.created_by, "Content-Type": "text/plain"}
        url = self.base + "/1.0/kb/tenants/uploadPluginConfig/killbill-email-notifications"
        req = urllib.request.Request(url, data=text.encode(), method="POST", headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status

    def add_external_pm(self, account_id: str):
        code, _, body = self.req(
            "POST", f"/1.0/kb/accounts/{account_id}/paymentMethods",
            params={"isDefault": "true"},
            body={"pluginName": EXTERNAL_PLUGIN, "pluginInfo": {}})
        if code != 201:
            raise RuntimeError(f"add_external_pm -> {code}: {body}")

    def subscribe(self, account_id: str, plan: str):
        code, loc, _ = self.req(
            "POST", "/1.0/kb/subscriptions",
            params={"callCompletion": "true", "callTimeoutSec": "15"},
            body={"accountId": account_id, "planName": plan})
        if code != 201 or not loc:
            raise RuntimeError(f"subscribe -> {code}")
        return loc.rsplit("/", 1)[-1]

    def subscription(self, sub_id: str) -> dict:
        _, _, body = self.req("GET", f"/1.0/kb/subscriptions/{sub_id}")
        return body

    def cancel(self, sub_id: str):
        code, _, body = self.req(
            "DELETE", f"/1.0/kb/subscriptions/{sub_id}",
            params={"entitlementPolicy": "END_OF_TERM", "billingPolicy": "END_OF_TERM",
                    "useRequestedDateForBilling": "false"})
        if code not in (200, 204):
            raise RuntimeError(f"cancel -> {code}: {body}")

    def invoices(self, account_id: str) -> list:
        """Invoice totals must be read PER-INVOICE: the account list endpoint
        reports amount/balance as 0.0 for every row (verified against 0.24.16)."""
        _, _, lst = self.req("GET", f"/1.0/kb/accounts/{account_id}/invoices")
        out = []
        for row in lst or []:
            _, _, full = self.req("GET", f"/1.0/kb/invoices/{row['invoiceId']}",
                                  params={"withItems": "true"})
            out.append(full)
        return out

    def payments(self, account_id: str) -> list:
        _, _, body = self.req("GET", f"/1.0/kb/accounts/{account_id}/payments")
        return body or []


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
class Fail(Exception):
    pass


def check(cond, msg):
    if not cond:
        raise Fail(msg)
    print(f"    assert OK: {msg}")


def poll(fn, desc, clock: Clock, timeout=45.0, interval=1.5):
    """Wait for an EVENT (a settled observable), not a fixed duration. Drains
    the KB queues between polls so async invoicing/payment completes."""
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            clock.wait_queues(timeout_sec=5)
        except Exception:
            pass
        val = fn()
        if val:
            return val
        last = val
        time.sleep(interval)
    raise Fail(f"timed out waiting for: {desc} (last={last!r})")


def date_at_noon(dt_or_date: str) -> str:
    """Take the date portion of an ISO datetime and return <date>T12:00:00.
    Noon is strictly past the 08:00-class event instants Kill Bill schedules,
    which is the guard against the FIXTURES §9 date-vs-datetime trap."""
    return dt_or_date[:10] + "T12:00:00"


def recurring_item(inv: dict, amount: float):
    for it in (inv or {}).get("items", []):
        if it.get("itemType") == "RECURRING" and abs(float(it["amount"]) - amount) < 1e-9:
            return it
    return None


def fixed_zero_item(inv: dict):
    for it in (inv or {}).get("items", []):
        if it.get("itemType") == "FIXED" and abs(float(it["amount"])) < 1e-9:
            return it
    return None


# --------------------------------------------------------------------------- #
# lifecycle
# --------------------------------------------------------------------------- #
def wait_healthy(kb: KB, timeout=180) -> None:
    url = kb.base + "/1.0/healthcheck"
    deadline = time.monotonic() + timeout
    print(f"  waiting for Kill Bill health at {url} ...")
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=4) as r:
                if r.status == 200:
                    print("  Kill Bill healthy.")
                    return
        except Exception:
            pass
        time.sleep(3)
    raise Fail("Kill Bill did not become healthy in time")


# --------------------------------------------------------------------------- #
# the proof
# --------------------------------------------------------------------------- #
def run(keep: bool, with_email: bool) -> int:
    load_env()
    timeline: list[tuple[str, str, str]] = []

    def vnow() -> str:
        return clock.get().get("currentUtcTime", "?")

    def step(action: str, evidence: str):
        timeline.append((vnow(), action, evidence))

    t_wall_start = time.time()

    print(f"[1/8] Cold start: docker compose down -v && up -d  (project {PROJECT})")
    sg_compose("down", "-v", "--remove-orphans")
    up = sg_compose("up", "-d")
    if up.returncode != 0:
        raise Fail("compose up failed")

    kb = KB()
    clock = Clock(base_url=kb.base)
    sink = None
    if Mailsink is not None:
        ui_port = os.environ.get("MAILPIT_UI_PORT", "8025")
        sink = Mailsink(base_url=f"http://127.0.0.1:{ui_port}")

    print("[2/8] Wait for services healthy")
    wait_healthy(kb)

    if with_email:
        print("[2b/8] Install email-notifications plugin (stretch: sink coupling)")
        # demo.py uploads the tenant config itself at [3/8] (after the tenant
        # exists), so tell the installer to skip that step here.
        r = subprocess.run([os.path.join(HERE, "install-email-plugin.sh")], cwd=HERE,
                           env={**os.environ, "NOSHIT_SKIP_TENANT_CONFIG": "1"})
        if r.returncode != 0:
            raise Fail("email plugin install failed")
        wait_healthy(kb)  # the plugin install restarts Kill Bill

    print("[3/8] Tenant + catalog")
    kb.create_tenant()
    with open(os.path.join(HERE, "catalog.xml")) as f:
        kb.upload_catalog(f.read())
    print("    tenant ready, catalog uploaded")
    if with_email:
        kb.upload_email_config(
            "org.killbill.billing.plugin.email-notifications.defaultEvents="
            "INVOICE_CREATION,INVOICE_PAYMENT_SUCCESS,SUBSCRIPTION_CANCEL")
        print("    email-notifications tenant config uploaded (events -> sink)")

    sink_ckpt = None
    if sink is not None:
        try:
            sink_ckpt = sink.checkpoint()  # (None, count) before any mail
            print(f"    mail sink reachable, {sink_ckpt[1]} message(s) held at checkpoint")
        except Exception as e:
            print(f"    mail sink not reachable ({e}); continuing (sink coupling is the documenso leg)")

    print(f"[4/8] Freeze virtual clock at T0 = {T0}")
    clock.set(T0, timeout_sec=5)
    step("set clock to T0", f"virtual now = {vnow()}")

    print("[5/8] Account + test payment method + subscribe")
    acct = kb.create_account()
    kb.add_external_pm(acct)
    sub_id = kb.subscribe(acct, PLAN)
    sub = kb.subscription(sub_id)
    trial_inv = poll(lambda: next((i for i in kb.invoices(acct) if fixed_zero_item(i)), None),
                     "trial ($0) invoice", clock)
    check(sub["state"] == "ACTIVE" and sub["phaseType"] == "TRIAL",
          f"subscription is ACTIVE in TRIAL (state={sub['state']}, phase={sub['phaseType']})")
    check(abs(float(trial_inv["amount"])) < 1e-9,
          f"trial invoice #{trial_inv['invoiceNumber']} totals $0.00")
    step(f"subscribe '{PLAN}' ({TRIAL_DAYS}-day trial)",
         f"trial invoice #{trial_inv['invoiceNumber']} = $0.00; entitlement ACTIVE/TRIAL")

    # The engine scheduled the exact trial->paid instant; cross it at noon.
    phase_evt = next(e for e in sub["events"] if e["eventType"] == "PHASE")
    convert_to = date_at_noon(phase_evt["effectiveDate"])
    print(f"[6/8] Move clock past trial end (PHASE @ {phase_evt['effectiveDate']}) -> {convert_to}")
    clock.set(convert_to, timeout_sec=10)

    conv_inv = poll(lambda: next((i for i in kb.invoices(acct) if recurring_item(i, MONTHLY_PRICE)), None),
                    f"conversion invoice (${MONTHLY_PRICE} RECURRING)", clock)
    paid = poll(lambda: next((p for p in kb.payments(acct)
                              if abs(float(p.get("purchasedAmount") or 0) - MONTHLY_PRICE) < 1e-9
                              and any(t["transactionType"] == "PURCHASE" and t["status"] == "SUCCESS"
                                      for t in p["transactions"])), None),
                f"successful ${MONTHLY_PRICE} charge", clock)
    sub = kb.subscription(sub_id)
    check(sub["phaseType"] == "EVERGREEN" and sub["state"] == "ACTIVE",
          f"subscription converted to EVERGREEN (state={sub['state']})")
    check(recurring_item(conv_inv, MONTHLY_PRICE) is not None,
          f"conversion invoice #{conv_inv['invoiceNumber']} has RECURRING ${MONTHLY_PRICE}")
    check(any(t["status"] == "SUCCESS" for t in paid["transactions"]),
          f"payment {paid['paymentNumber']} PURCHASE ${MONTHLY_PRICE} SUCCESS")
    step("clock crosses trial end (T0+8d)",
         f"invoice #{conv_inv['invoiceNumber']} RECURRING ${MONTHLY_PRICE}; "
         f"payment #{paid['paymentNumber']} PURCHASE ${MONTHLY_PRICE} SUCCESS; phase EVERGREEN")

    if with_email and sink is not None and sink_ckpt is not None:
        held = poll(lambda: (lambda n: n if n > sink_ckpt[1] else None)(sink.count()),
                    "invoice/payment email delivered to mailpit sink", clock)
        check(held > sink_ckpt[1],
              f"{held - sink_ckpt[1]} email(s) captured in mailpit sink (invoice + payment notices)")
        step("email-notifications -> sink", f"{held} message(s) in mailpit (SMTP -> mailpit:1025)")

    print("[7/8] Cancel (END_OF_TERM) and cross the period boundary")
    kb.cancel(sub_id)
    sub = kb.subscription(sub_id)
    boundary = sub.get("billingEndDate") or sub.get("cancelledDate")
    check(boundary is not None and sub["state"] == "ACTIVE",
          f"cancel is pending at period end {boundary} (state still ACTIVE)")
    step("cancel subscription (END_OF_TERM)",
         f"cancellation scheduled {boundary[:10]} (period boundary); entitlement still ACTIVE")

    cross_to = date_at_noon(boundary)
    print(f"    move clock to period end -> {cross_to}")
    clock.set(cross_to, timeout_sec=10)
    ended = poll(lambda: kb.subscription(sub_id) if kb.subscription(sub_id)["state"] == "CANCELLED" else None,
                 "entitlement CANCELLED", clock)
    check(ended["state"] == "CANCELLED", f"entitlement ended (state={ended['state']})")
    step("clock crosses period boundary",
         f"entitlement CANCELLED as of {ended.get('cancelledDate','?')[:10]}")

    # Sink status (coupling is proven on the documenso leg; here we report it).
    if sink is not None and sink_ckpt is not None:
        try:
            held = sink.count()
            step("check mail sink",
                 f"{held} message(s) in sink "
                 f"({'email-notifications plugin active' if held > sink_ckpt[1] else 'no plugin installed — see README'})")
        except Exception:
            pass

    print("\n" + "=" * 74)
    print("VIRTUAL-TIME TIMELINE  (clock moved by the engine, not wall time)")
    print("=" * 74)
    print(f"{'VIRTUAL TIME (UTC)':<26} {'ACTION':<34} EVIDENCE")
    print("-" * 74)
    for vt, action, ev in timeline:
        print(f"{vt:<26} {action:<34} {ev}")
    print("=" * 74)

    wall = time.time() - t_wall_start
    print(f"\nPASS — full trial→convert→charge→cancel cycle in {wall:.1f}s wall clock "
          f"(virtual span {T0[:10]} → {timeline[-1][0][:10] if timeline else '?'}).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Kill Bill engine-native clock proof (F0).")
    ap.add_argument("--keep", action="store_true",
                    help="leave the stack running after the run (default: tear down)")
    ap.add_argument("--with-email", action="store_true",
                    help="stretch: install the email-notifications plugin and assert "
                         "invoice/payment notices land in the mailpit sink (needs host internet)")
    args = ap.parse_args()

    rc = 1
    try:
        rc = run(args.keep, args.with_email)
    except Fail as e:
        print(f"\nFAIL: {e}", file=sys.stderr)
        rc = 1
    except Exception as e:  # noqa: BLE001
        print(f"\nERROR: {e}", file=sys.stderr)
        rc = 1
    finally:
        if args.keep:
            print(f"\n--keep: stack left running. Tear down with:\n"
                  f"  sg docker -c \"docker compose -p {PROJECT} down -v\"")
        else:
            print(f"\nTearing down (scoped): docker compose -p {PROJECT} down -v")
            sg_compose("down", "-v", "--remove-orphans")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
