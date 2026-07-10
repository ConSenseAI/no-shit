#!/usr/bin/env python3
"""
stripe-clockctl.py — No Shit / F0 platform proof, Ghost + Stripe leg.

Proves FIXTURES.md §2.1 rung 1 (engine-native clock) on the Stripe side:
a real Stripe *sandbox* test clock, started at a frozen T0, driven forward-only
through the exact time script an 8-day-trial subscription rides —
T0 -> T0+6d -> T0+8d+1h -> cancel boundary — in minutes of wall time.

CAPABILITY-ADAPTIVE. It probes the key first:

  * If the key can manage customers/subscriptions/invoices, `full-cycle` runs
    the FULL LIFECYCLE proof: create clock at T0, customer + 8-day-trial
    subscription (4242 card), advance to T0+6d (trial_will_end), advance past
    trial end (invoice finalized + paid), cancel at the period boundary.

  * If the key is test-clock-only (as the F0 sandbox restricted key is — see
    README "Scope denials"), `full-cycle` runs the CLOCK-MECHANICS proof: the
    same time script against a bare clock, asserting every advance lands its
    frozen_time exactly, that the forward-only invariant is enforced, and that
    each step respects the <=2-interval cap. Each script position is annotated
    with the subscription fact it *would* prove — marked BLOCKED-BY-SCOPE.

Security: the key is read from $STRIPE_SECRET_KEY or ./.env and never printed.
All output passes through mask() which redacts rk_/sk_/pk_/whsec_ tokens to
e.g. rk_test_*** — including error and exception text.

Subcommands:
  doctor                        probe the key; print the scope map
  full-cycle [opts]             run the proof (auto-selects lifecycle | clock)
      --keep                    do not delete the test clock at the end
      --json-log PATH           write a structured run log
      --clock-only              force the clock-mechanics proof
      --require-full            exit nonzero if lifecycle scopes are absent
  cleanup [--all]               delete leftover tool-owned test clocks
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None
    import urllib.parse
    import urllib.request
    import urllib.error

API_ROOT = "https://api.stripe.com/v1"
TOOL_TAG = "noshit-f0-ghost"
DAY = 86400
HOUR = 3600
MONTH = 30 * DAY  # nominal monthly interval for cap accounting / cancel step

# ---------------------------------------------------------------------------
# Secret masking — every byte of output goes through this.
# ---------------------------------------------------------------------------
_SECRET_RE = re.compile(r"(rk|sk|pk|whsec)_(test|live)_[A-Za-z0-9]+")
_LIVE_KEY = None


def mask(text) -> str:
    """Redact any Stripe secret from a string. Idempotent."""
    if text is None:
        return ""
    s = str(text)
    if _LIVE_KEY:
        s = s.replace(_LIVE_KEY, "rk_test_***")
    return _SECRET_RE.sub(lambda m: f"{m.group(1)}_{m.group(2)}_***", s)


def say(*parts) -> None:
    line = " ".join(mask(p) for p in parts)
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {line}", flush=True)


# ---------------------------------------------------------------------------
# Key loading
# ---------------------------------------------------------------------------
def load_key() -> str:
    global _LIVE_KEY
    key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not key:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path) as fh:
                for raw in fh:
                    raw = raw.strip()
                    if raw.startswith("STRIPE_SECRET_KEY="):
                        key = raw.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    if not key:
        sys.exit("FATAL: no STRIPE_SECRET_KEY in env or ./.env")
    if not key.startswith(("rk_test_", "sk_test_")):
        sys.exit("FATAL: key is not a test-mode key (must start rk_test_/sk_test_)")
    _LIVE_KEY = key
    return key


# ---------------------------------------------------------------------------
# Stripe client
# ---------------------------------------------------------------------------
class StripeError(Exception):
    def __init__(self, status, code, typ, message):
        self.status = status
        self.code = code
        self.typ = typ
        self.message = message or ""
        super().__init__(mask(f"HTTP {status} {typ}/{code}: {message}"))

    def denied(self):
        return self.status in (401, 403)

    def advancing(self):
        return self.status == 429 and "advancement underway" in self.message


def _flatten(params, parent=None):
    out = {}
    for k, v in params.items():
        key = f"{parent}[{k}]" if parent else str(k)
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        elif isinstance(v, (list, tuple)):
            for i, elem in enumerate(v):
                if isinstance(elem, dict):
                    out.update(_flatten(elem, f"{key}[{i}]"))
                else:
                    out[f"{key}[{i}]"] = elem
        elif isinstance(v, bool):
            out[key] = "true" if v else "false"
        elif v is None:
            continue
        else:
            out[key] = v
    return out


class Stripe:
    def __init__(self, key, api_version=None):
        self.key = key
        self.api_version = api_version

    def _headers(self):
        h = {"Authorization": f"Bearer {self.key}"}
        if self.api_version:
            h["Stripe-Version"] = self.api_version
        return h

    def request(self, method, path, params=None):
        url = f"{API_ROOT}{path}"
        data = _flatten(params or {})
        if requests is not None:
            resp = requests.request(
                method, url, headers=self._headers(),
                data=data if method != "GET" else None,
                params=data if method == "GET" else None,
                timeout=45,
            )
            status, body = resp.status_code, resp.text
        else:
            enc = urllib.parse.urlencode(data)
            if method == "GET" and enc:
                url, payload = f"{url}?{enc}", None
            else:
                payload = enc.encode() if enc else None
            req = urllib.request.Request(url, data=payload, method=method,
                                         headers=self._headers())
            try:
                with urllib.request.urlopen(req, timeout=45) as r:
                    status, body = r.status, r.read().decode()
            except urllib.error.HTTPError as e:
                status, body = e.code, e.read().decode()
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"_raw": body}
        if status >= 400:
            err = parsed.get("error", {})
            raise StripeError(status, err.get("code"), err.get("type"),
                              err.get("message", body))
        return parsed

    def get(self, path, params=None):
        return self.request("GET", path, params)

    def post(self, path, params=None):
        return self.request("POST", path, params)

    def delete(self, path, params=None):
        return self.request("DELETE", path, params)


# ---------------------------------------------------------------------------
# Clock helpers — async-safe (poll to ready; tolerate "advancement underway")
# ---------------------------------------------------------------------------
def poll_ready(s, clock_id, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        clock = s.get(f"/test_helpers/test_clocks/{clock_id}")
        st = clock["status"]
        if st == "ready":
            return clock
        if st == "internal_failure":
            raise StripeError(500, "internal_failure", "test_clock", "advance failed")
        time.sleep(2)
    raise StripeError(504, "timeout", "test_clock", "clock never became ready")


def advance_clock(s, clock_id, to_time, timeout=180):
    """POST an advance and block until the clock is ready. Tolerates a prior
    advance still settling (429 'advancement underway') by waiting it out."""
    poll_ready(s, clock_id, timeout)  # never POST onto an in-flight advance
    for attempt in range(4):
        try:
            s.post(f"/test_helpers/test_clocks/{clock_id}/advance",
                   {"frozen_time": to_time})
            break
        except StripeError as e:
            if e.advancing() and attempt < 3:
                poll_ready(s, clock_id, timeout)
                continue
            raise
    return poll_ready(s, clock_id, timeout)


def delete_clock(s, clock_id):
    """Poll ready, then delete (cascades customers + subscriptions)."""
    for attempt in range(4):
        try:
            poll_ready(s, clock_id, 180)
            s.delete(f"/test_helpers/test_clocks/{clock_id}")
            return True
        except StripeError as e:
            if e.advancing() and attempt < 3:
                time.sleep(3)
                continue
            raise
    return False


# ---------------------------------------------------------------------------
# Timeline collector
# ---------------------------------------------------------------------------
class Timeline:
    def __init__(self, t0):
        self.t0 = t0
        self.rows = []

    def mark(self, vt, label, detail=""):
        self.rows.append((vt - self.t0, vt, label, detail))

    @staticmethod
    def _fmt(secs):
        d, rem = divmod(secs, DAY)
        h, rem = divmod(rem, HOUR)
        m = rem // 60
        parts = []
        if d:
            parts.append(f"{d}d")
        if h:
            parts.append(f"{h}h")
        if m and not d:
            parts.append(f"{m}m")
        return "T0+" + "".join(parts) if parts else "T0"

    def render(self):
        out = ["", "=" * 74,
               "  VIRTUAL-TIME TIMELINE  (simulated clock, not wall time)",
               "=" * 74,
               f"  {'position':<10} {'sim UTC':<18} observation",
               "  " + "-" * 70]
        for offset, vt, label, detail in self.rows:
            pos = self._fmt(offset)
            simutc = datetime.fromtimestamp(vt, timezone.utc).strftime("%Y-%m-%d %H:%M")
            out.append(mask(f"  {pos:<10} {simutc:<18} {label}"))
            if detail:
                out.append(mask(f"  {'':<10} {'':<18}   -> {detail}"))
        out.append("=" * 74)
        return "\n".join(out)


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------
class AssertFail(Exception):
    pass


class Checks:
    def __init__(self):
        self.items = []

    def check(self, cond, msg):
        status = "PASS" if cond else "FAIL"
        self.items.append((status, msg))
        say(f"  [{status}] {msg}")
        if not cond:
            raise AssertFail(msg)

    def note(self, status, msg):
        self.items.append((status, msg))
        say(f"  [{status}] {msg}")

    def passed(self):
        return sum(1 for st, _ in self.items if st == "PASS")


# ---------------------------------------------------------------------------
# Capability probe
# ---------------------------------------------------------------------------
def capability(s):
    """Return a dict of which resource families this key can read."""
    caps = {}
    for name, path, params in (
        ("customers", "/customers", {"limit": 1}),
        ("subscriptions", "/subscriptions", {"limit": 1}),
        ("invoices", "/invoices", {"limit": 1}),
        ("events", "/events", {"limit": 1}),
        ("test_clocks", "/test_helpers/test_clocks", {"limit": 1}),
    ):
        try:
            s.get(path, params)
            caps[name] = True
        except StripeError as e:
            if e.denied():
                caps[name] = False
            else:
                raise
    caps["lifecycle"] = caps["customers"] and caps["subscriptions"]
    return caps


def _tag(extra=None):
    m = {"tool": TOOL_TAG}
    if extra:
        m.update(extra)
    return m


def _utc(ts):
    if ts is None:
        return "None"
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------
def cmd_doctor(s, args):
    say("DOCTOR: probing restricted-key scopes (test mode)")
    denials = []

    def probe(label, fn):
        try:
            fn()
            say(f"  [ok  ] {label}")
        except StripeError as e:
            if e.denied():
                say(f"  [DENY] {label}")
                denials.append(label)
            else:
                say(f"  [err ] {label}: {e}")

    for label, path in (
        ("read products", "/products"), ("read prices", "/prices"),
        ("read customers", "/customers"), ("read subscriptions", "/subscriptions"),
        ("read invoices", "/invoices"), ("read events", "/events"),
        ("read payment_methods", "/payment_methods"),
        ("read test_clocks", "/test_helpers/test_clocks"),
    ):
        p = {"limit": 1}
        if path == "/payment_methods":
            p["type"] = "card"
        probe(label, lambda path=path, p=p: s.get(path, p))

    made = None
    try:
        made = s.post("/test_helpers/test_clocks",
                      {"frozen_time": int(time.time()), "name": f"{TOOL_TAG}-doctor"})
        say(f"  [ok  ] create test_clock -> {made['id']}")
    except StripeError as e:
        say(f"  [DENY] create test_clock: {e}")
        denials.append("create test_clock")
    finally:
        if made:
            try:
                delete_clock(s, made["id"])
                say(f"  [ok  ] delete test_clock -> {made['id']}")
            except StripeError as e:
                say(f"  [warn] could not delete doctor clock: {e}")

    say("")
    if denials:
        say(f"DOCTOR: {len(denials)} scope denial(s): " + ", ".join(denials))
    else:
        say("DOCTOR: no scope denials on probed resources.")
    return 0


# ---------------------------------------------------------------------------
# Lifecycle proof (runs when the key has customer/subscription scope)
# ---------------------------------------------------------------------------
def _lifecycle_proof(s, args, caps):
    run_id = str(int(time.time()))
    log = []
    ck = Checks()
    wall_start = time.time()
    say(f"MODE: FULL LIFECYCLE (key has subscription scope)  run_id={run_id}")
    t0 = int(time.time())
    tl = Timeline(t0)
    product = price = clock = cust = None
    sub_id = None
    try:
        say("STEP 1  product + $12/mo price")
        product = s.post("/products", {"name": f"No Shit F0 Ghost ({run_id})",
                                       "metadata": _tag({"run": run_id})})
        price = s.post("/prices", {"product": product["id"], "unit_amount": 1200,
                                   "currency": "usd", "recurring": {"interval": "month"},
                                   "metadata": _tag({"run": run_id})})
        say(f"  product={product['id']} price={price['id']}")

        say("STEP 2  test clock frozen at T0")
        clock = s.post("/test_helpers/test_clocks",
                       {"frozen_time": t0, "name": f"{TOOL_TAG}-{run_id}"})
        tl.mark(t0, "clock frozen; subscription created", f"clock={clock['id']}")

        say("STEP 3  customer on the clock + 4242 card")
        cust = s.post("/customers", {"name": f"F0 Member {run_id}",
                                     "email": f"f0-ghost-{run_id}@example.test",
                                     "test_clock": clock["id"],
                                     "metadata": _tag({"run": run_id})})
        pm = s.post("/payment_methods/pm_card_visa/attach", {"customer": cust["id"]})
        s.post(f"/customers/{cust['id']}",
               {"invoice_settings": {"default_payment_method": pm["id"]}})

        say("STEP 4  subscription with 8-day trial")
        sub = s.post("/subscriptions", {"customer": cust["id"],
                                        "items": [{"price": price["id"]}],
                                        "trial_period_days": 8,
                                        "metadata": _tag({"run": run_id})})
        sub_id = sub["id"]
        ck.check(sub["status"] == "trialing",
                 f"subscription starts 'trialing' (got {sub['status']})")
        ck.check(abs(sub["trial_end"] - (t0 + 8 * DAY)) <= 2,
                 f"trial_end == T0+8d ({_utc(sub['trial_end'])})")
        tl.mark(sub["trial_end"], "trial scheduled to end", "8-day trial")

        say("STEP 5  advance -> T0+6d (cross trial_will_end trigger at T0+5d)")
        advance_clock(s, clock["id"], t0 + 6 * DAY)
        sub6 = s.get(f"/subscriptions/{sub_id}")
        ck.check(sub6["status"] == "trialing", f"still trialing at T0+6d ({sub6['status']})")
        detail = ""
        if caps["events"]:
            evs = s.get("/events", {"type": "customer.subscription.trial_will_end",
                                    "limit": 100, "created[gte]": t0})["data"]
            hit = next((e for e in evs
                        if e["data"]["object"].get("id") == sub_id), None)
            ck.check(hit is not None, "trial_will_end event observed")
            detail = f"event {hit['id']}" if hit else ""
        else:
            ck.note("BLOCKED", "trial_will_end event unreadable (events scope denied)")
            ck.check(sub6["trial_end"] > t0 + 6 * DAY,
                     "trial_end still ahead of clock (notice-window proxy)")
            detail = "events denied — proxy assertion"
        tl.mark(t0 + 6 * DAY, "clock at T0+6d; trial_will_end window crossed", detail)

        say("STEP 6  advance -> T0+8d+1h (trial ends; invoice finalizes + pays)")
        advance_clock(s, clock["id"], t0 + 8 * DAY + HOUR)
        sub8 = s.get(f"/subscriptions/{sub_id}")
        ck.check(sub8["status"] == "active", f"converted to active ({sub8['status']})")
        invs = s.get("/invoices", {"subscription": sub_id, "limit": 100})["data"]
        paid = [i for i in invs if i["status"] == "paid" and i["amount_paid"] > 0]
        ck.check(len(paid) >= 1, f"a finalized+paid invoice exists ({len(paid)})")
        ck.check(paid[0]["amount_paid"] == 1200,
                 f"conversion charge == $12.00 (${paid[0]['amount_paid']/100:.2f})")
        n_paid = len(paid)
        tl.mark(t0 + 8 * DAY + HOUR, "trial converted -> active; invoice charged",
                f"invoice {paid[0]['id']} paid ${paid[0]['amount_paid']/100:.2f}")

        say("STEP 7  cancel_at_period_end; advance to the boundary")
        s.post(f"/subscriptions/{sub_id}", {"cancel_at_period_end": True})
        cur = s.get(f"/subscriptions/{sub_id}")
        boundary = cur.get("current_period_end") or (t0 + 8 * DAY + MONTH)
        advance_clock(s, clock["id"], boundary + HOUR)
        subC = s.get(f"/subscriptions/{sub_id}")
        ck.check(subC["status"] == "canceled", f"canceled at boundary ({subC['status']})")
        invs2 = s.get("/invoices", {"subscription": sub_id, "limit": 100})["data"]
        paid2 = [i for i in invs2 if i["status"] == "paid" and i["amount_paid"] > 0]
        ck.check(len(paid2) == n_paid, f"no extra charge after cancel ({len(paid2)})")
        tl.mark(boundary + HOUR, "period boundary passed; subscription canceled",
                "cancellation honored — no further charge")

        print(tl.render())
        say("")
        say(f"RESULT: {ck.passed()}/{len(ck.items)} assertions passed "
            f"(wall {time.time()-wall_start:.1f}s)")
        say("FULL LIFECYCLE proven on the Stripe sandbox — floor + billing target met.")
        rc = 0
    except (AssertFail, StripeError) as e:
        say("")
        say(f"RESULT: FAILED — {e}")
        rc = 1
    finally:
        _finalize(s, args, clock, [price, product], log, run_id, t0, ck)
    return rc


# ---------------------------------------------------------------------------
# Clock-mechanics proof (runs when the key is test-clock-only)
# ---------------------------------------------------------------------------
def _clock_proof(s, args, caps):
    run_id = str(int(time.time()))
    log = []
    ck = Checks()
    wall_start = time.time()
    say(f"MODE: CLOCK-MECHANICS (key is test-clock-only)  run_id={run_id}")
    say("The subscription lifecycle is BLOCKED by key scope (see README).")
    say("This proves the clock harness the subscription would ride: frozen T0,")
    say("forward-only advances landing exact frozen_time, async poll-to-ready,")
    say("<=2-interval steps, delete-cascade. Each position notes the blocked fact.")
    say("")

    t0 = int(time.time())
    tl = Timeline(t0)
    clock = None

    # The time script an 8-day-trial subscription rides. (offset, would-prove)
    script = [
        (6 * DAY, "trial_will_end notice would fire (T0+5d, 3d before trial end)"),
        (8 * DAY + HOUR, "trial would convert -> active; invoice finalized + charged"),
        (8 * DAY + MONTH + HOUR, "cancel_at_period_end -> canceled at the boundary"),
    ]
    try:
        say("STEP 1  create test clock frozen at T0")
        clock = s.post("/test_helpers/test_clocks",
                       {"frozen_time": t0, "name": f"{TOOL_TAG}-{run_id}"})
        ck.check(clock["status"] == "ready", "clock created and 'ready'")
        ck.check(clock["frozen_time"] == t0, f"frozen_time == T0 ({_utc(t0)})")
        tl.mark(t0, "clock frozen at T0",
                "would create: customer + 8-day-trial sub (4242 card)  [BLOCKED: scope]")
        log.append({"kind": "clock_created", "clock": clock["id"], "t0": t0})

        prev = 0
        for offset, would in script:
            target = t0 + offset
            step = offset - prev
            ck.check(step <= 2 * MONTH,
                     f"advance step {Timeline._fmt(step)} within <=2-interval cap")
            say(f"STEP  advance -> {Timeline._fmt(offset)}")
            c = advance_clock(s, clock["id"], target)
            ck.check(c["status"] == "ready",
                     f"clock 'ready' after advance to {Timeline._fmt(offset)}")
            ck.check(c["frozen_time"] == target,
                     f"frozen_time landed exactly at {Timeline._fmt(offset)} "
                     f"({_utc(target)})")
            ck.note("BLOCKED", f"subscription fact @ {Timeline._fmt(offset)}: {would}")
            tl.mark(target, f"clock at {Timeline._fmt(offset)}",
                    f"{would}  [BLOCKED: scope]")
            log.append({"kind": "advanced", "offset": offset, "frozen": target,
                        "status": c["status"], "blocked_fact": would})
            prev = offset

        say("STEP  forward-only invariant: attempt a backward advance (must reject)")
        try:
            s.post(f"/test_helpers/test_clocks/{clock['id']}/advance",
                   {"frozen_time": t0 + DAY})
            ck.check(False, "backward advance rejected")
        except StripeError as e:
            ck.check(e.status == 400 and "forward" in e.message.lower(),
                     "backward advance rejected (forward-only invariant enforced)")
            log.append({"kind": "forward_only", "rejected": True})

        print(tl.render())
        say("")
        say(f"RESULT: {ck.passed()}/{len(ck.items)} clock assertions passed "
            f"(wall {time.time()-wall_start:.1f}s)")
        say("CLOCK MECHANICS proven. Subscription lifecycle BLOCKED by key scope —")
        say("drop in a key with customer/subscription/invoice/events scope and the")
        say("same 'full-cycle' auto-runs the full lifecycle proof.")
        rc_full_missing = 1 if args.require_full else 0
        rc = rc_full_missing if not caps["lifecycle"] else 0
    except (AssertFail, StripeError) as e:
        say("")
        say(f"RESULT: FAILED — {e}")
        rc = 1
    finally:
        _finalize(s, args, clock, [], log, run_id, t0, ck)
    return rc


def _finalize(s, args, clock, archivables, log, run_id, t0, ck):
    if args.json_log and log:
        with open(args.json_log, "w") as fh:
            json.dump({"run_id": run_id, "t0": t0, "events": log,
                       "checks": ck.items}, fh, indent=2, default=str)
    if clock and not args.keep:
        say("")
        say("CLEANUP: deleting test clock (cascades customers + subscriptions)")
        try:
            delete_clock(s, clock["id"])
            say(f"  deleted clock {clock['id']}")
        except StripeError as e:
            say(f"  [warn] clock delete failed: {e}")
        for obj, path in ((archivables[0] if archivables else None, "prices"),
                          (archivables[1] if len(archivables) > 1 else None, "products")):
            if obj:
                try:
                    s.post(f"/{path}/{obj['id']}", {"active": False})
                except StripeError:
                    pass
    elif args.keep and clock:
        say("")
        say(f"--keep: leaving clock {clock['id']}. Run 'cleanup' to remove later.")


def cmd_full_cycle(s, args):
    say("Detecting key capability ...")
    caps = capability(s)
    say("  capability: " + ", ".join(
        f"{k}={'yes' if v else 'no'}" for k, v in caps.items() if k != "lifecycle"))
    if caps["lifecycle"] and not args.clock_only:
        return _lifecycle_proof(s, args, caps)
    return _clock_proof(s, args, caps)


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------
def cmd_cleanup(s, args):
    say("CLEANUP: scanning for tool-owned test clocks")
    clocks = s.get("/test_helpers/test_clocks", {"limit": 100})["data"]
    ours = [c for c in clocks if (c.get("name") or "").startswith(TOOL_TAG)]
    say(f"  found {len(ours)} tool-owned clock(s)")
    for c in ours:
        try:
            delete_clock(s, c["id"])
            say(f"  deleted clock {c['id']} ({c.get('name')})")
        except StripeError as e:
            say(f"  [warn] delete {c['id']} failed: {e}")
    if args.all:
        try:
            prods = s.get("/products", {"limit": 100})["data"]
            for p in prods:
                if (p.get("metadata") or {}).get("tool") == TOOL_TAG and p.get("active"):
                    try:
                        s.post(f"/products/{p['id']}", {"active": False})
                        say(f"  archived product {p['id']}")
                    except StripeError:
                        pass
        except StripeError as e:
            if e.denied():
                say("  (products scope denied — nothing to archive; skipping)")
            else:
                raise
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main(argv=None):
    p = argparse.ArgumentParser(description="Stripe test-clock proof (No Shit F0)")
    p.add_argument("--api-version", default=os.environ.get("STRIPE_API_VERSION"))
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="probe key scopes")
    fc = sub.add_parser("full-cycle", help="run the proof")
    fc.add_argument("--keep", action="store_true")
    fc.add_argument("--json-log", default=None)
    fc.add_argument("--clock-only", action="store_true")
    fc.add_argument("--require-full", action="store_true")
    cl = sub.add_parser("cleanup", help="remove tool-owned test clocks")
    cl.add_argument("--all", action="store_true")
    args = p.parse_args(argv)

    s = Stripe(load_key(), api_version=args.api_version)
    if args.cmd == "doctor":
        return cmd_doctor(s, args)
    if args.cmd == "full-cycle":
        return cmd_full_cycle(s, args)
    if args.cmd == "cleanup":
        return cmd_cleanup(s, args)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print(mask(f"UNCAUGHT: {type(e).__name__}: {e}"), file=sys.stderr)
        sys.exit(1)
