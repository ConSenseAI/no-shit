#!/usr/bin/env python3
"""noshit-f1-discourse — E2 proof (F1 Discourse bench leg, Option A launcher).

Assumes the stack is UP (launcher-managed Discourse container + mailpit sink) and
provisioned (admin + API key minted by provision/admin_seed.rb; demo.sh handles
both). Proves the platform's services on a NEW host — production-parity Discourse:

  PHASE 0  preflight: sink reachable, app /srv/status 200, admin API key valid,
           messaging-determinism settings confirmed via API (printed).
  PHASE 1  FORUM UP on 127.0.0.1:8084 + admin created non-interactively.
  PHASE 2  SIGNUP E2 MAIL ROUND-TRIP: register a NEW user over plain HTTP
           (scrape CSRF + honeypot) -> activation email lands in the sink
           (checkpoint -> wait_new) -> follow the activation TOKEN from the real
           email body -> user is active (verified via the admin API).
  PHASE 3  EVENT-ANCHORED ABSENCE: after activation, drain sidekiq to its
           observable completion (not a timer), then checkpoint -> assert_none_new
           per-address AND census-wide (welcome+digest mail disabled; documented).
  PHASE 4  BULK SEED: >=50 topics via the admin API key in one deterministic pass
           (create rate limits lifted via API, recorded). Wall-time + verified.
  PHASE 5  SUBSCRIPTIONS PLUGIN, INSTALL-ONLY: bundled discourse-subscriptions is
           listed in /admin/plugins.json, its settings are registered, and its
           admin route is mounted (non-404) — with NO Stripe/payment config.
  PHASE 6  CLOCK-STORY NOTE for F2 (evidence only): container libc, where jobs
           run, scheduled-job enumerability/triggerability.
  PHASE 7  timeline + result.

Exits nonzero on any failed assertion. Every sink claim goes through
harness/mailsink.py (checkpoint / wait_new / assert_none_new / search).
"""
import html
import json
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "harness"))  # shared mailsink.py
from mailsink import Mailsink  # noqa: E402

PROJECT = "noshit-f1-discourse"
CONTAINER = "noshit-f1-discourse"
APP = "http://localhost:8084"          # == 127.0.0.1:8084; Host 'localhost' is canonical
SINK_URL = "http://127.0.0.1:8031"

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
    env = {}
    for line in (SCRIPT_DIR / ".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k] = v
    return env


def rails_file(fname, timeout=200):
    """Run /shared/<fname> via `rails runner` inside the launcher container as the
    discourse user (login shell for rbenv/bundle env). Returns stdout."""
    railscmd = f"bundle exec rails runner /shared/{fname}"
    inner = (f"docker exec -u discourse -w /var/www/discourse {CONTAINER} "
             f"bash -lc {shlex.quote(railscmd)}")
    r = subprocess.run(["sg", "docker", "-c", inner],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise DemoError(f"rails runner {fname} rc={r.returncode}: {(r.stderr or r.stdout)[-500:]}")
    return r.stdout.strip()


# --- admin API (Api-Key header; no cookie/CSRF needed) ----------------------
A = requests.Session()
A.headers["User-Agent"] = "noshit-f1-discourse-demo/1.0"
API_KEY = None
ADMIN_USERNAME = None


def adm(method, path, expect=None, **kw):
    h = kw.pop("headers", {})
    h["Api-Key"] = API_KEY
    h["Api-Username"] = ADMIN_USERNAME
    r = A.request(method, APP + path, headers=h, timeout=kw.pop("timeout", 40), **kw)
    if expect is not None and r.status_code not in expect:
        raise DemoError(f"{method} {path} -> {r.status_code} (expected {expect}): {r.text[:300]}")
    return r


def set_setting(name, value):
    v = "true" if value is True else "false" if value is False else str(value)
    r = adm("PUT", f"/admin/site_settings/{name}.json", data={name: v})
    say(f"site_setting {name}={v} -> {r.status_code}")
    return r.status_code == 200


def main():
    global API_KEY, ADMIN_USERNAME
    env = read_env()
    ADMIN_USERNAME = env.get("ADMIN_USERNAME", "noshit_admin")
    API_KEY = env.get("DISCOURSE_API_KEY")
    if not API_KEY:
        raise DemoError("DISCOURSE_API_KEY missing from .env — run ./demo.sh (it provisions the admin+key)")

    # ---------------------------------------------------------------- PHASE 0
    phase("PHASE 0 — preflight: sink, app health, admin API key, messaging state")
    sink = Mailsink(SINK_URL)
    for _ in range(60):
        try:
            say(f"sink reachable at {SINK_URL} ({sink.count()} message(s) held)")
            break
        except OSError:
            time.sleep(1)
    else:
        raise DemoError(f"mailpit sink not reachable at {SINK_URL}")

    for _ in range(240):   # app boot (migrations + unicorn) can take a while
        try:
            r = requests.get(APP + "/srv/status", timeout=10, allow_redirects=False)
            if r.status_code == 200:
                say(f"app health: GET /srv/status -> 200 ({r.text.strip()[:20]!r})")
                break
        except requests.RequestException:
            pass
        time.sleep(2)
    else:
        raise DemoError(f"app /srv/status never returned 200 at {APP}")

    about = adm("GET", "/about.json", expect=(200,)).json()
    ver = about.get("about", {}).get("version", "?")
    say(f"admin API key valid; Discourse version {ver}")

    say("confirming messaging-determinism site settings (set at provision; re-asserted here):")
    set_setting("allow_new_registrations", True)
    set_setting("must_approve_users", False)
    set_setting("send_welcome_message", False)
    set_setting("disable_digest_emails", True)

    # ---------------------------------------------------------------- PHASE 1
    phase("PHASE 1 — FORUM UP on 127.0.0.1:8084 + admin created non-interactively")
    plugins0 = adm("GET", "/admin/plugins.json", expect=(200,)).json()
    check(isinstance(plugins0, (list, dict)),
          "admin-gated GET /admin/plugins.json 200 -> admin API key authorized (admin exists)")
    home = requests.get(APP + "/", timeout=20)
    check(home.status_code == 200, f"homepage GET / -> {home.status_code}")
    record(f"forum up on 127.0.0.1:8084 (Discourse {ver}); admin '{ADMIN_USERNAME}' active, API key authorized")

    # ---------------------------------------------------------------- PHASE 2
    phase("PHASE 2 — SIGNUP E2 mail round-trip (user's real entry point, plain HTTP)")
    S = requests.Session()
    S.headers["User-Agent"] = "noshit-f1-discourse-demo/1.0 (signup)"
    S.headers["X-Requested-With"] = "XMLHttpRequest"

    csrf = S.get(APP + "/session/csrf.json", timeout=15).json()["csrf"]
    # Honeypot endpoint verified against the pinned source: config/routes.rb has
    # `get "session/hp" => "session#get_honeypot_value"` (NOT the older /u/hp.json).
    hp = S.get(APP + "/session/hp.json", timeout=15).json()
    say(f"endpoint requirements scraped: CSRF token from /session/csrf.json; honeypot from "
        f"/session/hp.json (password_confirmation=<value>, challenge=reverse(<challenge>))")

    runid = int(time.time())
    signup_email = f"f1-signup-{runid}@noshit.test"
    username = f"f1user{runid}"
    password = "F1-bench-Pass-234x"

    cp_signup = sink.checkpoint(f"to:{signup_email}")
    payload = {
        "name": "F1 Bench Signup",
        "username": username,
        "email": signup_email,
        "password": password,
        "password_confirmation": hp["value"],          # honeypot: must equal hp value
        "challenge": hp["challenge"][::-1],            # honeypot: reversed challenge
    }
    r = S.post(APP + "/u.json", data=payload,
               headers={"X-CSRF-Token": csrf}, timeout=30)
    check(r.status_code == 200, f"POST /u.json (signup) -> {r.status_code}")
    body = r.json()
    check(body.get("success") is True,
          f"signup accepted: success={body.get('success')} active={body.get('active')} "
          f"(msg: {str(body.get('message'))[:60]!r})")
    check(body.get("active") is False,
          "signup requires email activation (active=false) — the mail round-trip is real, not skipped")
    # LIVE-RESPONSE FIX: at this core SHA the signup JSON does NOT include
    # user_id (first run returned only success/active/message). Resolve the id
    # via the admin users list filtered by the address instead.
    user_id = body.get("user_id")
    if not user_id:
        lst = adm("GET", "/admin/users/list/all.json",
                  params={"filter": signup_email, "show_emails": "true"},
                  expect=(200,)).json()
        matches = [u for u in lst
                   if u.get("email") == signup_email or u.get("username") == username]
        check(bool(matches), "new user resolvable via admin users list (email filter)")
        user_id = matches[0]["id"]
        say(f"user_id resolved via admin list filter: {user_id} (signup JSON omits it at this version)")
    record(f"signup POST accepted over plain HTTP (csrf+honeypot); user_id={user_id}, awaiting activation email")

    msg = sink.wait_new(cp_signup, timeout=90)
    full = sink.message(msg["ID"])
    mail_body = (full.get("Text") or "") + "\n" + (full.get("HTML") or "")
    say(f"activation mail in sink: subject={msg.get('Subject')!r} to={signup_email}")
    # Token constraint verified against the pinned source: /[0-9a-f]+/ (hex only).
    m = re.search(r"/u/activate-account/([0-9a-f]{16,})", html.unescape(mail_body))
    check(bool(m), "activation email body carries an /u/activate-account/<token> link")
    token = m.group(1)
    record(f"activation email delivered to sink and parsed (token {token[:10]}...)")

    # Follow the activation from the email: the emailed URL points at
    # DISCOURSE_HOSTNAME (localhost:80, unmapped); we submit the TOKEN against the
    # mapped loopback port 8084 — the token is what the server validates.
    # Verified against the pinned source: the perform route is PUT, and
    # users#perform_account_activation RE-CHECKS the honeypot
    # (`raise InvalidAccess if honeypot_or_challenge_fails?(params)`), so the PUT
    # must carry password_confirmation + challenge again (same session's values).
    S.get(f"{APP}/u/activate-account/{token}", timeout=20)      # loads SPA page
    csrf2 = S.get(APP + "/session/csrf.json", timeout=15).json()["csrf"]
    hp2 = S.get(APP + "/session/hp.json", timeout=15).json()
    act_fields = {"password_confirmation": hp2["value"],
                  "challenge": hp2["challenge"][::-1]}
    ract = S.put(f"{APP}/u/activate-account/{token}.json", data=act_fields,
                 headers={"X-CSRF-Token": csrf2}, timeout=20)
    if ract.status_code in (404, 405):
        ract = S.post(f"{APP}/u/activate-account/{token}.json", data=act_fields,
                      headers={"X-CSRF-Token": csrf2}, timeout=20)
    say(f"submitted activation (PUT + honeypot fields) -> {ract.status_code}")

    urec = adm("GET", f"/admin/users/{user_id}.json", expect=(200,)).json()
    check(urec.get("active") is True,
          f"user #{user_id} is ACTIVE per admin API after following the emailed activation link")
    record(f"mail round-trip CLOSED: {signup_email} signed up -> emailed -> activated -> active")

    # ---------------------------------------------------------------- PHASE 3
    phase("PHASE 3 — EVENT-ANCHORED ABSENCE (anchored to sidekiq drain, not a timer)")
    say("draining sidekiq to observable completion (Discourse mails via sidekiq) ...")
    drain = rails_file("sidekiq_drain.rb")
    for line in drain.splitlines():
        say(f"    sidekiq | {line}")
    check("enqueued=0" in drain, "sidekiq immediate queue drained to 0 (mail jobs have run) — window may open")
    record(f"sidekiq drained (observable completion): {drain.splitlines()[-1]}")

    cp_addr = sink.checkpoint(f"to:{signup_email}")   # per-address baseline AFTER drain
    cp_all = sink.checkpoint()                         # census-wide baseline
    sink.assert_none_new(cp_addr, settle=4.0)
    check(True, f"ABSENCE holds per-address: no further mail to {signup_email} after activation "
                "(welcome message + digests disabled; settle covers delivery latency only)")
    sink.assert_none_new(cp_all, settle=0.5)
    check(True, "ABSENCE holds census-wide: no unexpected mail since the drain event")
    record("absence window held (opened by activation-arrived + sidekiq-drained; closed after settle)")

    # ---------------------------------------------------------------- PHASE 4
    phase("PHASE 4 — BULK SEED: >=50 topics via the admin API key, one pass")
    say("lifting create rate limits via the admin API (recorded):")
    for k, v in (("rate_limit_create_topic", 0), ("rate_limit_create_post", 0),
                 ("unique_posts_mins", 0), ("max_topics_per_day", 1000)):
        set_setting(k, v)

    # find-or-create a category to seed into
    cats = adm("GET", "/categories.json", expect=(200,)).json()["category_list"]["categories"]
    cat = next((c for c in cats if c["name"] == "F1 Bench"), None)
    if cat:
        cat_id, cat_slug = cat["id"], cat["slug"]
        say(f"reusing category 'F1 Bench' id={cat_id}")
    else:
        rc = adm("POST", "/categories.json",
                 data={"name": "F1 Bench", "color": "49d9e9", "text_color": "FFFFFF"},
                 expect=(200,)).json()["category"]
        cat_id, cat_slug = rc["id"], rc["slug"]
        say(f"created category 'F1 Bench' id={cat_id} slug={cat_slug}")

    N = 55
    seed_ids = []
    seed_errors = []
    stalls = 0
    seed_start = time.monotonic()
    for i in range(N):
        title = f"F1 Bench seed {runid}-{i:03d} — deterministic bulk topic for the Discourse leg"
        raw = (f"Seed post {runid}-{i:03d}. Deterministic bulk content proving admin-API topic "
               f"creation on this host. Unique body index {i} run {runid}.")
        data = {"title": title, "raw": raw, "category": cat_id}
        rp = adm("POST", "/posts.json", data=data)
        if rp.status_code == 429:
            # Admin-API request limiter (global max_admin_api_reqs_per_minute).
            # The leg raises it via env (see yml), so this path should be idle
            # here — kept as the portable fallback: honor the server's wait and
            # retry once. Recorded in the output (stall count) if it fires.
            try:
                wait_s = int(rp.json().get("extras", {}).get("wait_seconds", 30))
            except (ValueError, AttributeError):
                wait_s = 30
            stalls += 1
            say(f"seed {i:03d}: 429 rate-limited; honoring wait_seconds={wait_s} then retrying once")
            time.sleep(wait_s + 1)
            rp = adm("POST", "/posts.json", data=data)
        if rp.status_code == 200:
            seed_ids.append(rp.json()["topic_id"])
        else:
            seed_errors.append((i, rp.status_code, rp.text[:120]))
    seed_wall = time.monotonic() - seed_start

    distinct = sorted(set(seed_ids))
    say(f"seed pass: {len(distinct)} distinct topics created in {seed_wall:.1f}s "
        f"({len(seed_errors)} error(s), {stalls} rate-limit stall(s))")
    if seed_errors:
        say(f"    first error: {seed_errors[0]}")
    check(len(distinct) >= 50, f"bulk seed proof: {len(distinct)} topics >= 50 via admin API in one pass")

    # verify via the API: spot-check 3 created topics resolve
    sample = distinct[:3]
    for tid in sample:
        rt = adm("GET", f"/t/{tid}.json", expect=(200,)).json()
        check(rt.get("id") == tid, f"created topic #{tid} verified via API (title {rt.get('title','')[:34]!r})")
    record(f"bulk seed: {len(distinct)} topics in {seed_wall:.1f}s (admin API, category 'F1 Bench'); "
           f"{len(sample)} spot-verified")

    # ---------------------------------------------------------------- PHASE 5
    phase("PHASE 5 — SUBSCRIPTIONS PLUGIN, INSTALL-ONLY (bundled; prove it loads)")
    plist = adm("GET", "/admin/plugins.json", expect=(200,)).json()
    plugins = plist if isinstance(plist, list) else plist.get("plugins", [])
    subs = next((p for p in plugins if p.get("name") == "discourse-subscriptions"), None)
    check(subs is not None, "discourse-subscriptions listed in /admin/plugins.json (bundled in core)")
    say(f"plugin entry: name={subs.get('name')} enabled={subs.get('enabled')} "
        f"version={subs.get('version')} setting={subs.get('enabled_setting')}")

    # enable the bundled plugin (install-only; NO Stripe keys are ever set)
    set_setting("discourse_subscriptions_enabled", True)
    plist2 = adm("GET", "/admin/plugins.json", expect=(200,)).json()
    plugins2 = plist2 if isinstance(plist2, list) else plist2.get("plugins", [])
    subs2 = next((p for p in plugins2 if p.get("name") == "discourse-subscriptions"), {})
    check(subs2.get("enabled") is True, "discourse-subscriptions reports enabled=true after enabling its setting")

    # admin route mounted? Engine mounts at /s (verified in the pinned plugin.rb:
    # `mount DiscourseSubscriptions::Engine, at: "s"`). /s/admin is the engine's
    # `scope "admin"` index (no route constraint, controller-level auth);
    # /s/admin/{subscriptions,products,plans} sit behind AdminConstraint (which
    # may not see API-key auth -> 404 there is possible without meaning
    # "unmounted"). A non-404 on ANY of them proves the plugin's routes are
    # mounted = plugin loaded. (Index actions call Stripe, so a
    # Stripe-unconfigured error status still proves the route exists.)
    mounted = None
    for route in ("/s/admin.json", "/s/admin", "/s/admin/subscriptions.json",
                  "/s/admin/products.json", "/s/admin/plans.json"):
        rr = adm("GET", route)
        say(f"plugin admin route {route} -> {rr.status_code}")
        if rr.status_code != 404 and mounted is None:
            mounted = (route, rr.status_code)
    check(mounted is not None,
          f"plugin admin route mounted (non-404): {mounted and mounted[0]} -> {mounted and mounted[1]}")

    # Stripe-free corroboration + confirm NO payment config was applied
    ss = adm("GET", "/admin/site_settings.json", expect=(200,)).json()["site_settings"]
    sub_settings = {s["setting"]: s.get("value", "") for s in ss
                    if s["setting"].startswith("discourse_subscriptions")}
    check(bool(sub_settings), f"plugin registered its site settings ({len(sub_settings)} discourse_subscriptions_* keys)")
    keyish = {k: v for k, v in sub_settings.items() if "key" in k or "secret" in k}
    unconfigured = all(not v for v in keyish.values())
    check(unconfigured, f"INSTALL-ONLY confirmed: no Stripe keys set {list(keyish)} — all blank")
    record(f"plugin loaded: listed+enabled, admin route {mounted[0]} mounted ({mounted[1]}), "
           f"{len(sub_settings)} settings registered, ZERO payment config")

    # ---------------------------------------------------------------- PHASE 6
    phase("PHASE 6 — CLOCK-STORY NOTE for F2 (evidence only, no assertion)")
    note = rails_file("clock_note.rb")
    for line in note.splitlines():
        say(f"    clock | {line}")
    record("clock note captured (libc / sidekiq / scheduled-job enumerability) — see PHASE 6 output")

    # ---------------------------------------------------------------- PHASE 7
    phase("PHASE 7 — timeline")
    print(f"{'WALL':>8}  EVENT", flush=True)
    print("-" * 74, flush=True)
    for w, desc in TIMELINE:
        print(f"{w:>8}  {desc}", flush=True)

    phase("RESULT — F1 Discourse bench proofs")
    for line in (
        f"  forum    : Discourse {ver} up on 127.0.0.1:8084; admin '{ADMIN_USERNAME}' (API key)",
        f"  signup   : plain-HTTP /u.json (scraped CSRF + honeypot) -> activation mail -> "
        f"token followed -> user #{user_id} ACTIVE",
        "  absence  : per-address + census-wide, anchored to sidekiq drain (not a timer)",
        f"  seed     : {len(distinct)} topics via admin API in {seed_wall:.1f}s (one pass)",
        f"  plugin   : discourse-subscriptions bundled, listed+enabled, admin route mounted, "
        "install-only (no Stripe config)",
    ):
        print(line, flush=True)
    say(f"ALL ASSERTIONS PASSED in {time.monotonic() - _t0:.1f}s (sink holds {sink.count()} message(s))")


if __name__ == "__main__":
    try:
        main()
    except (DemoError, TimeoutError, AssertionError) as e:
        print(f"\n[{_wall()}] FAIL  {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
