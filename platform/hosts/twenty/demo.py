#!/usr/bin/env python3
"""noshit-f1-twenty — end-to-end E2 + messaging proof.

Assumes the stack is up and healthy and seed.py has run (demo.sh handles
up/seed/down). Drives Twenty's REAL API (auth on /metadata, data on /graphql +
/rest) and makes every sink claim through harness/mailsink.py:

  PHASE 0  preflight: sink reachable, Twenty healthy, founder state present.
  PHASE 1  USER-PATH ENTRY: log in over plain HTTP through the app's own auth
           endpoints (getLoginTokenFromCredentials -> getAuthTokensFromLoginToken)
           and assert the resulting token works against a real API read
           (companies/people totalCount via GraphQL AND a REST read).
  PHASE 2  MAIL -> SINK PRESENCE: send a workspace-member INVITE (sendInvitations)
           to a fresh address; checkpoint -> wait_new; assert the captured message
           matches (recipient, subject) and that the emailed invite link targets
           http://localhost:3001 (SERVER_URL correctness) — proving the multi-user
           surface AND host-reachable links.
  PHASE 3  EVENT-ANCHORED ABSENCE: anchored on the invite-DELIVERED event (not a
           timer), assert (a) a fresh never-invited control address received
           NOTHING and (b) no residual/duplicate mail followed the single invite
           to the invited address. This is the residual-messaging absence shape
           (FIXTURES §2.2 / O-2): absence windows close on completed-delivery
           events, settle margins cover transport latency only.
  PHASE 4  (optional nli bonus) export the companies collection to CSV via the
           REST API into captures/; assert row count >= the seeded count.
  PHASE 5  timeline + result.

Exits nonzero on any failed assertion.
"""
import csv
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))                          # seed.py
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "harness"))  # shared mailsink.py

from mailsink import Mailsink                       # noqa: E402
from seed import (                                   # noqa: E402
    TwentyClient, TwentyError, wait_healthy, load_state,
    APP_URL, SINK_URL, TARGET_COMPANIES, TARGET_PEOPLE, WORKSPACE_NAME,
)

RUN = str(int(time.time()))
CAPTURES_DIR = os.environ.get("TWENTY_CAPTURES_DIR",
                              "/home/user/fixture-runtime/twenty/captures")
LINK_RE = re.compile(r"https?://localhost:3001/invite/[0-9a-fA-F-]{20,}\?inviteToken=[^\s\"'<>)]+")

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
    say(f"TIMELINE  {stage:<20} {desc}")


class DemoError(Exception):
    pass


def check(cond, msg):
    if cond:
        say(f"PASS  {msg}")
    else:
        raise DemoError(msg)


def main():
    # ---------------------------------------------------------------- PHASE 0
    phase("PHASE 0 — preflight (sink, Twenty, founder state, seed)")
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
    client = TwentyClient()
    state = load_state()
    check(bool(state.get("email") and state.get("password")),
          f"founder state present (email={state.get('email')})")

    # ---------------------------------------------------------------- PHASE 1
    phase("PHASE 1 — USER-PATH ENTRY (login over HTTP -> authenticated API read)")
    # The app's OWN auth endpoints, over plain HTTP — the user's entry point.
    access = client.login(state["email"], state["password"])
    record("login", f"{state['email']} logged in via /metadata auth endpoints (HTTP)")
    c_total = client.count_companies(access)
    p_total = client.count_people(access)
    check(c_total >= TARGET_COMPANIES,
          f"authenticated GraphQL read: companies.totalCount={c_total} (>= {TARGET_COMPANIES} seeded)")
    check(p_total >= TARGET_PEOPLE,
          f"authenticated GraphQL read: people.totalCount={p_total} (>= {TARGET_PEOPLE} seeded)")
    st, body = client.rest("/rest/companies?limit=1", token=access)
    rest_total = body.get("totalCount") if isinstance(body, dict) else None
    check(st == 200 and rest_total == c_total,
          f"authenticated REST read: GET /rest/companies -> HTTP {st}, totalCount={rest_total}")
    record("read", f"token authorizes real reads (GraphQL {c_total} companies / {p_total} people; REST 200)")

    # roles for the invite
    member_role = client.role_id(access, "Member") or client.role_id(access, "Admin")
    check(bool(member_role), "resolved a workspace role id for the invite")

    # ---------------------------------------------------------------- PHASE 2
    phase("PHASE 2 — MAIL -> SINK PRESENCE (workspace invite -> captured email)")
    invitee = f"invitee-{RUN}@fixture.test"
    control = f"control-{RUN}@fixture.test"   # never invited (PHASE 3 absence)
    cp_inv = sink.checkpoint(f"to:{invitee}")
    cp_ctl = sink.checkpoint(f"to:{control}")           # baseline 0, taken BEFORE the send
    res = client.send_invitations([invitee], member_role, access)
    check(res.get("success") is True and any(r.get("email") == invitee for r in res.get("result", [])),
          f"sendInvitations returned success for {invitee}")
    record("invite", f"invite sent to {invitee} (role id={member_role})")

    msg = sink.wait_new(cp_inv, timeout=30)             # EVENT: invite delivered
    record("invite", f"invite email captured in sink (to:{invitee})")
    full = sink.message(msg["ID"])
    subject = full.get("Subject") or msg.get("Subject") or ""
    to_addrs = [a.get("Address", "") for a in (full.get("To") or [])]
    check(invitee in to_addrs or any(invitee in str(t) for t in (msg.get("To") or [])),
          f"captured message is addressed to {invitee} (To={to_addrs or msg.get('To')})")
    check("twenty" in subject.lower() or "team" in subject.lower() or "invit" in subject.lower(),
          f"subject matches an invite: {subject!r}")
    blob = (full.get("HTML") or "") + "\n" + (full.get("Text") or "")
    m = LINK_RE.search(blob)
    check(bool(m), "captured email carries an /invite/... link with an inviteToken")
    link = m.group(0)
    check(link.startswith("http://localhost:3001/invite/") and "inviteToken=" in link,
          f"emailed link targets http://localhost:3001 (SERVER_URL correct): {link[:72]}...")
    # NB the /invite/<uuid> segment is the workspace INVITE HASH, not the
    # workspace id — so we assert host/shape, not the workspace uuid.
    record("invite", f"link -> {link[:60]}... (host-reachable, SERVER_URL correct)")

    # ---------------------------------------------------------------- PHASE 3
    phase("PHASE 3 — EVENT-ANCHORED ABSENCE (residual-messaging shape)")
    # Anchor: the invite-DELIVERED event above (sink.wait_new returned), NOT a
    # timer. The send flow is complete, so nothing is queued-but-unsent.
    say("anchor = invite delivered (PHASE 2 event); settle window covers transport latency only")
    # (a) a fresh, never-invited control address must have received NOTHING.
    sink.assert_none_new(cp_ctl, settle=3.0)
    ctl_now = sink.count(f"to:{control}")
    check(ctl_now == 0, f"control address {control} received 0 mail (never targeted) — absence holds")
    record("absence", f"0 mail to never-invited {control} (anchored on invite-delivered)")
    # (b) no residual/duplicate mail followed the single invite to the invitee.
    cp_after = sink.checkpoint(f"to:{invitee}")         # baseline = the 1 invite
    sink.assert_none_new(cp_after, settle=4.0)
    inv_now = sink.count(f"to:{invitee}")
    check(inv_now == 1,
          f"exactly 1 message to {invitee} — no residual/duplicate mail after the invite (count={inv_now})")
    record("absence", f"no residual mail to {invitee} after its single invite (still {inv_now})")

    # ---------------------------------------------------------------- PHASE 4
    phase("PHASE 4 — CSV export via REST (optional nli bonus)")
    csv_result = "skipped"
    try:
        os.makedirs(CAPTURES_DIR, exist_ok=True)
        rows, cursor, pages = [], None, 0
        first_total = None
        while True:
            path = "/rest/companies?limit=60&order_by=createdAt" + (f"&starting_after={cursor}" if cursor else "")
            st, body = client.rest(path, token=access)
            if st != 200 or not isinstance(body, dict):
                raise DemoError(f"REST paging failed at page {pages + 1}: HTTP {st}")
            recs = body.get("data", {}).get("companies", [])
            if first_total is None:
                first_total = body.get("totalCount")
            for r in recs:
                dn = r.get("domainName") or {}
                rows.append([r.get("id"), r.get("name"),
                             dn.get("primaryLinkUrl", "") if isinstance(dn, dict) else "",
                             r.get("createdAt")])
            pages += 1
            pi = body.get("pageInfo") or {}
            if not recs or not pi.get("hasNextPage") or pages > 50:
                break
            cursor = pi.get("endCursor")
        out_path = os.path.join(CAPTURES_DIR, f"companies-{RUN}.csv")
        with open(out_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "name", "domainName", "createdAt"])
            w.writerows(rows)
        check(len(rows) == first_total,
              f"CSV export enumerated all {len(rows)} companies (== REST totalCount {first_total})")
        check(len(rows) >= TARGET_COMPANIES,
              f"exported {len(rows)} rows to {out_path} (>= {TARGET_COMPANIES} seeded)")
        record("export", f"{len(rows)} companies -> {out_path} ({pages} REST pages)")
        csv_result = f"{len(rows)} rows"
    except (DemoError, OSError, KeyError, TypeError) as e:
        say(f"CSV export bonus skipped: {type(e).__name__}: {e}")
        csv_result = "skipped"

    # ---------------------------------------------------------------- PHASE 5
    phase("PHASE 5 — timeline")
    print(f"{'STAGE':<22}{'WALL':>8}  EVENT", flush=True)
    print("-" * 74, flush=True)
    for stage, w, desc in TIMELINE:
        print(f"{stage:<22}{w:>8}  {desc}", flush=True)

    phase("RESULT — host bring-up + seeding + messaging capture + absence proven")
    for line in (
        f"  user-path entry   : {state['email']} login -> token -> real API read (GraphQL + REST)",
        f"  seed present      : {c_total} companies + {p_total} people (>= {TARGET_COMPANIES}/{TARGET_PEOPLE})",
        f"  mail -> sink      : workspace invite to {invitee} captured; link -> http://localhost:3001/invite/...",
        f"  absence (anchored): 0 to control {control}; no residual to {invitee} (anchor: invite-delivered)",
        f"  CSV export (bonus): {csv_result}",
    ):
        print(line, flush=True)
    say(f"ALL ASSERTIONS PASSED in {time.monotonic() - _t0:.1f}s wall time")


if __name__ == "__main__":
    try:
        main()
    except (DemoError, TwentyError, TimeoutError, AssertionError) as e:
        print(f"\n[{_wall()}] FAIL  {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
