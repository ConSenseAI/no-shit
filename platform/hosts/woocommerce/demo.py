#!/usr/bin/env python3
"""noshit-f1-woocommerce — E2 flow proof (F1 WooCommerce bench leg).

Assumes the stack is up, installed, and seeded (demo.sh orchestrates). Drives
a REAL customer checkout over plain HTTP against 127.0.0.1:8083 — "starts
where the user starts" (shop archive → add-to-cart → checkout form POST via
?wc-ajax=checkout with a scraped nonce + session cookie) and "ends where the
user cares" (order-received page, the store's order record, and the
order-confirmation mail in the sink).

  PHASE 0  preflight: sink reachable, app 200, seeding census (>=120 / >=3)
  PHASE 1  browse + add-to-cart over plain HTTP (session cookie proof)
  PHASE 2  checkout form -> scrape nonce -> POST ?wc-ajax=checkout (COD gateway)
  PHASE 3  store-record cross-check (wp wc shop_order get) + order-received page
  PHASE 4  sink PRESENCE: customer confirmation + admin new-order mail, order
           number cross-checked against the store record
  PHASE 5  rung-3 clock story: DISABLE_WP_CRON=true; wp cron event list; the
           harness fires due jobs explicitly (wp cron event run --due-now)
  PHASE 6  sink ABSENCE: window anchored between COMPLETED events — it opens
           after the order settles + cron flush #1 completes, and closes when
           cron flush #2 completes; assert_none_new holds over it. No bare
           timers anchor the window (settle= covers delivery latency only).
  PHASE 7  timeline

Exits nonzero on any failed assertion. All sink claims go through
harness/mailsink.py (checkpoint / wait_new / assert_none_new / search).
"""
import html
import json
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "harness"))  # shared mailsink.py

from mailsink import Mailsink  # noqa: E402

PROJECT = "noshit-f1-woocommerce"
APP = "http://127.0.0.1:8083"
SINK_URL = "http://127.0.0.1:8028"

_t0 = time.monotonic()


def _wall():
    return f"{time.monotonic() - _t0:6.1f}s"


def say(msg):
    print(f"[{_wall()}] {msg}", flush=True)


def phase(title):
    print("\n" + "=" * 74, flush=True)
    print(f"== {title}", flush=True)
    print("=" * 74, flush=True)


TIMELINE = []


def record(desc):
    TIMELINE.append((_wall().strip(), desc))
    say(f"TIMELINE  {desc}")


class DemoError(Exception):
    pass


def check(cond, msg):
    if cond:
        say(f"PASS  {msg}")
    else:
        raise DemoError(msg)


def read_env():
    """Read the non-secret identifiers demo needs from .env (admin user name +
    admin email). The .env is never printed; the password key is never read."""
    env = {}
    for line in (SCRIPT_DIR / ".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k] = v
    return env


def wp(args, timeout=240):
    """Run `wp <args>` in the leg's wpcli tools container. Returns stdout.
    Raises DemoError on nonzero exit (stderr tail included — no secrets pass
    through wp-cli stdout/stderr in this leg)."""
    inner = f"docker compose -p {PROJECT} run --rm -T wpcli wp {args}"
    r = subprocess.run(
        ["sg", "docker", "-c", inner],
        cwd=str(SCRIPT_DIR),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        raise DemoError(f"wp {args.split('--user')[0]} failed rc={r.returncode}: "
                        f"{(r.stderr or r.stdout)[-400:]}")
    return r.stdout.strip()


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def find_href(html_text, marker_res):
    """First href matched by any regex in marker_res (attr order varies)."""
    for rx in marker_res:
        m = re.search(rx, html_text, re.S)
        if m:
            return html.unescape(m.group(1))
    return None


def main():
    env = read_env()
    admin_user = env["WP_ADMIN_USER"]     # not a secret (fixture identifier)
    admin_email = env["WP_ADMIN_EMAIL"]   # not a secret
    cust_email = f"f1-customer-{int(time.time())}@noshit.test"

    S = requests.Session()
    S.headers["User-Agent"] = "noshit-f1-woocommerce-demo/1.0 (requests)"

    # ---------------------------------------------------------------- PHASE 0
    phase("PHASE 0 — preflight: sink, app, seeding census")
    sink = Mailsink(SINK_URL)
    for _ in range(60):
        try:
            say(f"sink reachable at {SINK_URL} ({sink.count()} message(s) held)")
            break
        except OSError:
            time.sleep(1)
    else:
        raise DemoError(f"mailpit sink not reachable at {SINK_URL}")

    for _ in range(120):
        try:
            r = S.get(APP + "/", timeout=10)
            if r.status_code == 200:
                say(f"app serving: GET / -> {r.status_code} ({len(r.text)} bytes)")
                break
        except requests.ConnectionError:
            pass
        time.sleep(1)
    else:
        raise DemoError(f"app not serving 200 at {APP}/")

    n_products = int(wp("post list --post_type=product --post_status=publish --format=count"))
    cats = json.loads(wp("term list product_cat --fields=slug,count --format=json"))
    nonempty = {c["slug"]: int(c["count"]) for c in cats
                if c["slug"] != "uncategorized" and int(c["count"]) > 0}
    say(f"seeding census: {n_products} published products; categories: {nonempty}")
    check(n_products >= 120, f"seeding proof holds: {n_products} products >= 120")
    check(len(nonempty) >= 3, f"seeding proof holds: {len(nonempty)} non-empty categories >= 3")
    record(f"census: {n_products} products across {len(nonempty)} categories")

    # ---------------------------------------------------------------- PHASE 1
    phase("PHASE 1 — browse + add-to-cart over plain HTTP (user's entry point)")
    r = S.get(APP + "/?post_type=product", timeout=15)
    check(r.status_code == 200, f"GET /?post_type=product (shop archive) -> {r.status_code}")
    pids = re.findall(r'data-product_id="(\d+)"', r.text)
    check(bool(pids), f"shop archive lists purchasable products ({len(pids)} add-to-cart buttons on page 1)")
    pid = pids[0]
    say(f"picking first archive product: product_id={pid}")

    r = S.post(APP + "/?wc-ajax=add_to_cart",
               data={"product_id": pid, "quantity": "2"},
               headers={"X-Requested-With": "XMLHttpRequest"}, timeout=15)
    check(r.status_code == 200, f"POST /?wc-ajax=add_to_cart -> {r.status_code}")
    aj = r.json()
    check("error" not in aj and aj.get("fragments"),
          "add_to_cart returned cart fragments (no error)")
    sess_cookies = [c.name for c in S.cookies if c.name.startswith("wp_woocommerce_session_")]
    check(bool(sess_cookies), f"WooCommerce session cookie set over plain HTTP ({sess_cookies[0][:30]}...)")
    record(f"add-to-cart: product {pid} x2 in session cart (plain HTTP)")

    frags = "".join(v for v in aj["fragments"].values() if isinstance(v, str))
    cart_url = find_href(frags, [r'href="([^"]+)"[^>]*class="[^"]*wc-forward',
                                 r'class="[^"]*wc-forward[^"]*"[^>]*href="([^"]+)"'])
    if cart_url:
        say(f"cart URL discovered from mini-cart fragment: {cart_url}")
    else:
        cart_url = f"{APP}/?page_id={wp('option get woocommerce_cart_page_id')}"
        say(f"cart URL from store config (fragment had no link): {cart_url}")

    r = S.get(cart_url, timeout=15)
    check(r.status_code == 200 and "cart" in r.text.lower(), f"GET cart page -> {r.status_code}")
    checkout_url = find_href(r.text, [r'href="([^"]+)"[^>]*class="[^"]*checkout-button',
                                      r'class="[^"]*checkout-button[^"]*"[^>]*href="([^"]+)"'])
    if checkout_url:
        say(f"checkout URL discovered from cart page: {checkout_url}")
    else:
        checkout_url = f"{APP}/?page_id={wp('option get woocommerce_checkout_page_id')}"
        say(f"checkout URL from store config (no button found): {checkout_url}")
    record("cart page shows the item; checkout link followed (user path)")

    # ---------------------------------------------------------------- PHASE 2
    phase("PHASE 2 — checkout form -> nonce scrape -> ?wc-ajax=checkout POST (COD)")
    r = S.get(checkout_url, timeout=15)
    check(r.status_code == 200, f"GET checkout page -> {r.status_code}")
    m = re.search(r'name="woocommerce-process-checkout-nonce"[^>]*value="([a-f0-9]+)"', r.text)
    check(bool(m), "scraped woocommerce-process-checkout-nonce from the checkout form")
    nonce = m.group(1)
    check('value="cod"' in r.text or 'payment_method_cod' in r.text,
          "offline COD gateway offered on the checkout form")

    # sink checkpoints BEFORE the order is placed (presence baselines)
    cp_cust = sink.checkpoint(f"to:{cust_email}")
    cp_admin = sink.checkpoint(f"to:{admin_email}")

    fields = {
        "billing_first_name": "Casey", "billing_last_name": "Fixture",
        "billing_company": "", "billing_country": "US",
        "billing_address_1": "1 Bench Way", "billing_address_2": "",
        "billing_city": "San Francisco", "billing_state": "CA",
        "billing_postcode": "94107", "billing_phone": "555-0100",
        "billing_email": cust_email, "order_comments": "",
        "payment_method": "cod",
        "woocommerce-process-checkout-nonce": nonce,
        "_wp_http_referer": "/?wc-ajax=update_order_review",
    }
    r = S.post(APP + "/?wc-ajax=checkout", data=fields,
               headers={"X-Requested-With": "XMLHttpRequest"}, timeout=30)
    check(r.status_code == 200, f"POST /?wc-ajax=checkout -> {r.status_code}")
    try:
        cj = r.json()
    except ValueError:
        raise DemoError(f"checkout response not JSON: {r.text[:300]!r}")
    if cj.get("result") != "success":
        raise DemoError(f"checkout failed: {strip_tags(cj.get('messages', ''))[:400]}")
    redirect = html.unescape(cj["redirect"])
    q = urllib.parse.parse_qs(urllib.parse.urlparse(redirect).query)
    order_id = (q.get("order-received") or [None])[0]
    order_key = (q.get("key") or [""])[0]
    check(bool(order_id and order_key.startswith("wc_order_")),
          f"checkout succeeded over plain HTTP: order #{order_id} ({order_key[:14]}...)")
    record(f"CHECKOUT via ?wc-ajax=checkout POST: order #{order_id} placed (guest, COD)")

    # ---------------------------------------------------------------- PHASE 3
    phase("PHASE 3 — 'ends where the user cares': order-received page + store record")
    r = S.get(redirect, timeout=15)
    check(r.status_code == 200 and str(order_id) in r.text,
          f"order-received page renders order #{order_id} to the customer")

    rec = json.loads(wp(f"wc shop_order get {order_id} "
                        f"--user={admin_user} --fields=id,status,total,billing --format=json"))
    say(f"store record: id={rec['id']} status={rec['status']} total={rec['total']} "
        f"billing.email={rec['billing']['email']}")
    check(int(rec["id"]) == int(order_id), "store order record id matches the checkout redirect")
    check(rec["status"] in ("processing", "on-hold"),
          f"COD order settled into offline-gateway status {rec['status']!r}")
    check(rec["billing"]["email"] == cust_email, "store record carries the customer's email")
    record(f"order #{order_id} verified in store records (status={rec['status']}, total={rec['total']})")

    # ---------------------------------------------------------------- PHASE 4
    phase("PHASE 4 — sink PRESENCE: order mail captured + order number cross-check")
    deferred = False
    try:
        m_cust = sink.wait_new(cp_cust, timeout=60)
    except TimeoutError:
        # Fixture-grade cron is OFF (DISABLE_WP_CRON): if this host defers order
        # mail to a scheduled job, fire due jobs explicitly (rung 3) and re-wait.
        deferred = True
        say("customer mail not synchronous — firing due cron jobs (rung-3 trigger) ...")
        wp("cron event run --due-now")
        m_cust = sink.wait_new(cp_cust, timeout=30)
    say(f"customer mail: subject={m_cust.get('Subject')!r} to={cust_email}")
    check(bool(m_cust), "order-confirmation email reached the customer in the sink"
                        + (" (via explicit cron trigger)" if deferred else " (synchronous)"))

    m_admin = sink.wait_new(cp_admin, timeout=30)
    say(f"admin mail: subject={m_admin.get('Subject')!r} to={admin_email}")

    full_c = sink.message(m_cust["ID"])
    body_c = (full_c.get("Text") or "") + (full_c.get("HTML") or "")
    check(str(order_id) in body_c,
          f"customer confirmation body cites order #{order_id} (matches store record)")
    m_num = re.search(r"#\s*(\d+)", m_admin.get("Subject") or "")
    if m_num:
        check(m_num.group(1) == str(order_id),
              f"admin new-order subject cites order #{m_num.group(1)} == store record")
    else:
        body_a = sink.message(m_admin["ID"])
        check(str(order_id) in ((body_a.get("Text") or "") + (body_a.get("HTML") or "")),
              f"admin new-order body cites order #{order_id}")
    record(f"presence: customer + admin order mail for #{order_id} in sink"
           + (" [deferred->cron-triggered]" if deferred else ""))

    # ---------------------------------------------------------------- PHASE 5
    phase("PHASE 5 — rung-3 clock story: DISABLE_WP_CRON + harness-triggered jobs")
    flag = wp("config get DISABLE_WP_CRON").strip().lower()
    check(flag in ("1", "true"), f"DISABLE_WP_CRON={flag}: page-hit cron OFF (fixture-grade)")
    ev = wp("cron event list --fields=hook,next_run_relative")
    lines = ev.splitlines()
    say(f"wp cron event list: {max(0, len(lines) - 1)} scheduled hooks; first few:")
    for line in lines[:8]:
        say(f"    | {line}")
    flush1 = wp("cron event run --due-now")
    n1 = (re.search(r"total of (\d+) cron event", flush1) or [None, "?"])[1]
    say(f"cron flush #1 completed: executed {n1} due event(s) under harness control")
    check("Executed" in flush1 or "No cron events" in flush1,
          "harness-triggered job run completed (wp cron event run --due-now)")
    record(f"rung-3: cron flush #1 executed {n1} due job(s) — COMPLETED event")

    # ---------------------------------------------------------------- PHASE 6
    phase("PHASE 6 — sink ABSENCE: window anchored between completed events")
    say("window opens NOW: order settled (PH3/PH4) and cron flush #1 completed (PH5)")
    cp_all = sink.checkpoint()                       # census-wide baseline
    cp_cust2 = sink.checkpoint(f"to:{cust_email}")   # per-address baseline
    flush2 = wp("cron event run --due-now")          # the COMPLETED event that closes the window
    n2 = (re.search(r"total of (\d+) cron event", flush2) or [None, "?"])[1]
    say(f"cron flush #2 completed: executed {n2} due event(s) — closes the window")
    sink.assert_none_new(cp_all, settle=4.0)
    check(True, "ABSENCE holds census-wide: no unexpected mail between the two "
                "completed cron flushes (settle covers delivery latency only)")
    sink.assert_none_new(cp_cust2, settle=0.5)
    check(True, f"ABSENCE holds per-address: no further mail to {cust_email} after settle")
    record("absence window held (opened by settled order + flush #1, closed by flush #2)")

    # msg-channel census listing (FIXTURES §2.2): everything the sink holds.
    # The sink is recreated per stack-up, so this is exactly this run's mail.
    say("sink census — every message this run produced (newest last):")
    for m in reversed(sink._get("/api/v1/messages", limit=50)["messages"]):
        tos = ",".join(a.get("Address", "") for a in (m.get("To") or []))
        say(f"    | {m.get('Subject')!r} -> {tos}")

    # ---------------------------------------------------------------- PHASE 7
    phase("PHASE 7 — timeline")
    print(f"{'WALL':>8}  EVENT", flush=True)
    print("-" * 74, flush=True)
    for w, desc in TIMELINE:
        print(f"{w:>8}  {desc}", flush=True)

    phase("RESULT — F1 WooCommerce bench proofs")
    for line in (
        f"  seeding  : {n_products} products / {len(nonempty)} categories (wall-time in seed.sh output)",
        f"  checkout : plain-HTTP ?wc-ajax=checkout (scraped nonce + session cookie) -> order #{order_id}",
        f"  presence : customer + admin order mail in sink, order number cross-checked"
        + (" [customer mail via rung-3 trigger]" if deferred else ""),
        "  absence  : census-wide + per-address, anchored between completed cron flushes",
        "  clock    : DISABLE_WP_CRON=true; jobs fire only via wp cron event run --due-now (rung 3)",
    ):
        print(line, flush=True)
    say(f"ALL ASSERTIONS PASSED in {time.monotonic() - _t0:.1f}s wall time "
        f"(sink now holds {sink.count()} message(s))")


if __name__ == "__main__":
    try:
        main()
    except (DemoError, TimeoutError, AssertionError) as e:
        print(f"\n[{_wall()}] FAIL  {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
