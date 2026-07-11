#!/usr/bin/env python3
"""noshit-f1-plausible — end-to-end E2 + messaging proof.

Assumes the stack is up and healthy and seed.py has run (demo.sh handles
up/seed/down). Drives Plausible CE's REAL surfaces (registration LiveView over
websocket, classic HTTP login/activate/site, the /api/event tracking endpoint,
the authenticated dashboard JSON) and makes every sink claim through
harness/mailsink.py:

  PHASE 0  preflight: sink reachable, Plausible healthy, founder state present.
  PHASE 1  REGISTRATION MAIL ROUND-TRIP: register a FRESH user over plain HTTP
           (the register LiveView is driven over its own websocket — the ONLY
           non-classic step; login/activate are classic HTTP) with email
           verification ENABLED -> the 4-digit activation code lands in the sink
           -> extract it from the REAL email body -> POST /activate -> prove an
           authenticated call (GET /sites) now succeeds. This is the round-trip.
  PHASE 2  SITE + INGEST + READBACK (§2.3): on the seeded founder site, fire a
           fresh >=500-event pass at POST /api/event (the SAME endpoint the
           tracking script uses) and prove the dashboard aggregate CONVERGES to
           exactly baseline + pageviews-sent (ClickHouse buffered visibility).
  PHASE 3  PRESENCE + ABSENCE PAIR (event-anchored, per FIXTURES §2.2): the
           PRESENCE is the Phase-1 activation email; the ABSENCE, anchored on the
           activation-COMPLETED event (not a timer), is (a) a never-touched
           control address receiving 0 mail (census-wide) and (b) no residual /
           duplicate mail to the registered user after its activation settles.
  PHASE 4  CLOCK-STORY NOTE for F2 (no proof): image libc, where scheduled jobs
           run, and Plausible's native clock-shaped messaging as F2 targets.
  PHASE 5  timeline + result.

Exits nonzero on any failed assertion.
"""
import os
import sys
import time
import urllib.parse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))                          # seed.py
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "harness"))  # shared mailsink.py

from mailsink import Mailsink                       # noqa: E402
from seed import (                                   # noqa: E402
    PlausibleClient, PlausibleError, wait_healthy, load_state, seed_events,
    gen_password, APP_URL, SINK_URL, SITE_DOMAIN, SEED_PAGEVIEWS,
)

RUN = str(int(time.time()))
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


def record(stage, desc):
    TIMELINE.append((stage, _wall().strip(), desc))
    say(f"TIMELINE  {stage:<22} {desc}")


class DemoError(Exception):
    pass


def check(cond, msg):
    if cond:
        say(f"PASS  {msg}")
    else:
        raise DemoError(msg)


def main():
    # ---------------------------------------------------------------- PHASE 0
    phase("PHASE 0 — preflight (sink, Plausible, founder state)")
    sink = Mailsink(SINK_URL)
    for _ in range(60):
        try:
            say(f"sink reachable at {SINK_URL} ({sink.count()} message(s) held)")
            break
        except OSError:
            time.sleep(1)
    else:
        raise DemoError(f"mailpit sink not reachable at {SINK_URL}")

    wait_healthy(APP_URL, timeout=120)
    state = load_state()
    check(bool(state.get("email") and state.get("password")),
          f"founder state present (email={state.get('email')})")
    domain = state.get("domain", SITE_DOMAIN)

    # ---------------------------------------------------------------- PHASE 1
    phase("PHASE 1 — REGISTRATION MAIL ROUND-TRIP (fresh user, verification ON)")
    fresh_email = f"demo-{RUN}@fixture.test"
    control_email = f"control-{RUN}@fixture.test"   # never touched (PHASE 3 absence)
    cp_fresh = sink.checkpoint(f"to:{fresh_email}")
    cp_control = sink.checkpoint(f"to:{control_email}")   # baseline 0, taken up front
    say(f"registering fresh user {fresh_email} over plain HTTP "
        f"(LiveView register event over websocket) ...")
    client = PlausibleClient()
    code = client.register_and_activate(fresh_email, "F1 Demo User",
                                        gen_password(), sink)
    record("register", f"{fresh_email} registered; activation code emailed + captured")

    # the activation email is the PRESENCE half of the pair
    presence = sink.count(f"to:{fresh_email}")
    check(presence >= 1,
          f"activation email present in sink for {fresh_email} (count={presence}); "
          f"4-digit code {code} extracted from the REAL body and submitted to /activate")

    # authenticated call must now succeed (verified user, live session). The client
    # does NOT follow redirects, so an UNauthenticated GET /sites would be a 302 to
    # /login; a 200 proves the activated session authorizes the read.
    ac, sites_html, _ = client.get("/sites")
    check(ac == 200,
          f"authenticated GET /sites -> HTTP {ac} (activation succeeded; session authorizes real reads)")
    record("activate", f"{fresh_email} verified; authenticated GET /sites -> 200")

    # ---------------------------------------------------------------- PHASE 2
    phase("PHASE 2 — SITE + INGEST + READBACK via the REAL /api/event path (§2.3)")
    founder = PlausibleClient()
    founder.login(state["email"], state["password"])
    say(f"logged in as founder {state['email']}; seeded site = {domain}")
    r = seed_events(founder, domain, sink, pageviews=SEED_PAGEVIEWS)
    say(f"ingestion-cache readiness: ~{r['ingest_ready_secs']:.1f}s "
        f"(fresh sites drop events until the sites_by_domain cache refreshes)")
    say(f"fired {r['total_events']} events ({r['pageviews_sent']} pageviews) in "
        f"{r['send_wall']:.2f}s ({r['rate']:.0f} events/s); accepted={r['accepted']} dropped={r['dropped']}")
    check(r["dropped"] == 0,
          f"0 events dropped at POST /api/event (all {r['accepted']} accepted, x-plausible-dropped absent)")
    check(r["converged"],
          f"ClickHouse buffered visibility: dashboard pageviews converged to "
          f"{r['target_pv']} (+{r['pageviews_sent']}) ~{r['converge_secs']:.1f}s after send")
    check(r["final_pv"] == r["target_pv"],
          f"readback EQUALS sent: dashboard Total pageviews {r['final_pv']} == "
          f"baseline {r['baseline_pv']} + {r['pageviews_sent']} sent")
    record("ingest", f"{r['pageviews_sent']} pageviews via /api/event -> dashboard "
                     f"pageviews {r['baseline_pv']}->{r['final_pv']} (readback==sent)")

    # ---------------------------------------------------------------- PHASE 3
    phase("PHASE 3 — PRESENCE + ABSENCE PAIR (event-anchored, FIXTURES §2.2)")
    say("anchor = activation-COMPLETED event for the fresh user (PHASE 1), NOT a timer")
    # (a) census-wide: a never-touched control address received NOTHING.
    sink.assert_none_new(cp_control, settle=3.0)
    ctl_now = sink.count(f"to:{control_email}")
    check(ctl_now == 0,
          f"control address {control_email} received 0 mail (never targeted) — census-wide absence")
    record("absence", f"0 mail to never-touched {control_email}")
    # (b) per-address: no residual/duplicate mail to the user after activation settled.
    cp_after = sink.checkpoint(f"to:{fresh_email}")     # baseline = the activation mail(s)
    sink.assert_none_new(cp_after, settle=4.0)
    fresh_now = sink.count(f"to:{fresh_email}")
    check(fresh_now == cp_after[1],
          f"no residual mail to {fresh_email} after activation settled "
          f"(still {fresh_now}) — per-address absence; PRESENCE was the activation email")
    record("absence", f"no residual to {fresh_email} post-activation (still {fresh_now})")

    # ---------------------------------------------------------------- PHASE 4
    phase("PHASE 4 — CLOCK-STORY NOTE for F2 (no proof, orientation only)")
    for line in (
        "image libc      : Alpine 3.22 / musl (verified: /lib/libc.musl-x86_64.so.1;",
        "                  Dockerfile FROM alpine 3.22.2). => F2 rung-2 fake time uses the",
        "                  GLIBC-SIDECAR libfaketime pattern (as twenty/documenso/mastodon),",
        "                  NOT a direct musl LD_PRELOAD.",
        "scheduled work  : Oban cron inside the BEAM (config_env :ce => is_selfhost, base_cron",
        "                  only). Workers are ENUMERABLE + harness-triggerable via the release:",
        "                    bin/plausible rpc 'Plausible.Workers.<W>.new(%{}) |> Oban.insert()'",
        "                    bin/plausible rpc 'Plausible.Workers.<W>.perform(%Oban.Job{args: %{}})'",
        "                  DISABLE_CRON=true turns cron+queues off entirely (a clean rung-3 gate).",
        "native clocks   : F2 targets — ScheduleEmailReports (0 * * * *) enqueues WEEKLY/MONTHLY",
        "                  traffic-report emails; TrafficChangeNotifier (*/15) fires SPIKE/DROP",
        "                  notifications; SendSiteSetupEmails + SendCheckStatsEmails drive the",
        "                  onboarding email drip. Those longitudinal report emails are exactly the",
        "                  messaging the platform's virtual clock exists to COMPRESS (days->minutes).",
    ):
        print("   " + line, flush=True)
    record("clock-note", "musl/Alpine; Oban base_cron enumerable+triggerable; report/spike emails = F2 targets")

    # ---------------------------------------------------------------- PHASE 5
    phase("PHASE 5 — timeline")
    print(f"{'STAGE':<24}{'WALL':>8}  EVENT", flush=True)
    print("-" * 74, flush=True)
    for stage, w, desc in TIMELINE:
        print(f"{stage:<24}{w:>8}  {desc}", flush=True)

    phase("RESULT — host bring-up + seeding + registration round-trip + absence proven")
    for line in (
        f"  registration RT   : {fresh_email} -> WS register -> activation code {code} in sink "
        f"-> /activate -> authed GET /sites 200",
        f"  ingest + readback : {r['pageviews_sent']} pageviews via POST /api/event -> dashboard "
        f"Total pageviews {r['baseline_pv']}->{r['final_pv']} (==sent; converge ~{r['converge_secs']:.1f}s)",
        f"  presence + absence: presence=activation mail; absence=0 to {control_email} + "
        f"no residual to {fresh_email} (anchor: activation-completed)",
        f"  clock note        : musl/Alpine -> glibc-sidecar; Oban report/spike emails = F2 targets",
    ):
        print(line, flush=True)
    say(f"ALL ASSERTIONS PASSED in {time.monotonic() - _t0:.1f}s wall time")


if __name__ == "__main__":
    try:
        main()
    except (DemoError, PlausibleError, TimeoutError, AssertionError) as e:
        print(f"\n[{_wall()}] FAIL  {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
