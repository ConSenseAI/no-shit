#!/usr/bin/env python3
"""noshit-f1-listmonk — end-to-end E2 flow proof.

Assumes the stack is up and healthy (demo.sh handles up/seed/down). Drives
listmonk's REAL API + public unsubscribe flow, and makes every sink claim
through harness/mailsink.py:

  PHASE 0  preflight: sink reachable, listmonk healthy, admin login, seed present
  PHASE 1  CAMPAIGN -> SINK: create + start a campaign to the list; wait until the
           campaign FINISHES (event, not a timer) and the expected message volume
           lands in the sink. Delivered count vs subscriber count.
  PHASE 2  UNSUBSCRIBE ROUND-TRIP: pick a still-subscribed member; fetch THEIR
           actual campaign email from the sink; extract {{ UnsubscribeURL }} from
           the body; complete the unsubscribe over plain HTTP against the app;
           verify via the admin API that their list subscription is now
           `unsubscribed`.
  PHASE 3  PER-ADDRESS ABSENCE: checkpoint the sink scoped to the unsubscribed
           address; send a SECOND campaign to the same list; assert (a) the
           still-subscribed members received it (presence) and (b) the
           unsubscribed address received NOTHING new (absence) after the second
           campaign has FINISHED delivering. This presence+absence pair in one
           script window is the deliverable (ATTAINABILITY O-2).
  PHASE 4  (optional) double opt-in: subscribe -> confirmation mail in sink ->
           follow confirm link -> state flips to `confirmed`.
  PHASE 5  timeline.

Exits nonzero on any failed assertion.
"""
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))                          # seed.py
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "harness"))  # shared mailsink.py

from mailsink import Mailsink                       # noqa: E402
import seed                                          # noqa: E402
from seed import (                                   # noqa: E402
    ListmonkAdmin, wait_healthy, configure_messaging, ensure_list,
    seed_subscribers, APP_URL, SINK_URL, MAIN_LIST, OPTIN_LIST, SUB_COUNT,
    SMTP_HOST, SMTP_PORT,
)

RUN = str(int(time.time()))
UNSUB_RE = re.compile(r"https?://[^\s\"'<>)]+/subscription/[0-9a-fA-F-]{20,}/[0-9a-fA-F-]{20,}")
OPTIN_RE = re.compile(r"https?://[^\s\"'<>)]+/subscription/optin/([0-9a-fA-F-]{20,})")

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


# --- plain-HTTP helpers for the PUBLIC (unauthenticated) surfaces ------------
def http_get(url):
    req = urllib.request.Request(url, headers={"Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def http_post_form(url, form):
    data = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


# --- listmonk-specific helpers ----------------------------------------------
def list_total(admin, list_id):
    """Real-time count of subscribers on a list (SELECT count via the
    subscribers query). NB: listmonk's list.subscriber_count comes from the
    `mat_list_subscriber_stats` MATERIALIZED VIEW, which is refreshed on a
    schedule and is stale right after seeding/unsubscribing — so it is NOT used
    for any assertion here. The authoritative recipient count is a campaign's
    `to_send`, computed by a real query when the campaign starts."""
    st, _res, total = admin.query_subscribers(list_id, per_page=1)
    return total


def wait_campaign_finished(admin, camp_id, timeout=180, poll=0.5):
    deadline = time.monotonic() + timeout
    last = "?"
    while time.monotonic() < deadline:
        st, c = admin.get_campaign(camp_id)
        if isinstance(c, dict):
            last = c.get("status")
            if last == "finished":
                return c
            if last in ("cancelled",):
                raise DemoError(f"campaign {camp_id} ended {last}: {c}")
        time.sleep(poll)
    raise TimeoutError(f"campaign {camp_id} not finished within {timeout}s (last={last})")


def wait_count(sink, query, target, timeout=90, poll=0.5):
    deadline = time.monotonic() + timeout
    last = -1
    while time.monotonic() < deadline:
        last = sink.count(query)
        if last >= target:
            return last
        time.sleep(poll)
    raise TimeoutError(f"only {last}/{target} messages matching {query!r} within {timeout}s")


CAMPAIGN_BODY = (
    "<h1>{title}</h1>"
    "<p>No Shit F1 bench — Listmonk leg. This is a fixture campaign to the "
    "public list; no study content.</p>"
    '<p><a href="{{{{ UnsubscribeURL }}}}">Unsubscribe from this list</a>.</p>'
)


def run_campaign(admin, name, subject, list_id, template_id):
    body = CAMPAIGN_BODY.format(title=subject)
    st, camp = admin.create_campaign(name, subject, [list_id], body,
                                     from_email="f1-bench@fixture.test",
                                     template_id=template_id)
    if st not in (200, 201) or not isinstance(camp, dict):
        raise DemoError(f"create campaign -> {st}: {str(camp)[:200]}")
    st, _ = admin.start_campaign(camp["id"])
    if st != 200:
        raise DemoError(f"start campaign {camp['id']} -> {st}")
    return camp


def main():
    # ---------------------------------------------------------------- PHASE 0
    phase("PHASE 0 — preflight (sink, listmonk, admin, seed)")
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
    admin = ListmonkAdmin()
    admin.login()
    say(f"listmonk healthy at {APP_URL}; logged in as Super Admin")

    configure_messaging(admin, APP_URL, SMTP_HOST, SMTP_PORT)
    say(f"messaging -> sink confirmed (SMTP {SMTP_HOST}:{SMTP_PORT}, root_url={APP_URL})")

    lst = ensure_list(admin, MAIN_LIST, optin="single")
    list_id = lst["id"]
    total = list_total(admin, list_id)
    if total < SUB_COUNT:
        say(f"seeding subscribers (have {total}, want {SUB_COUNT}) ...")
        created, existing, wall = seed_subscribers(admin, list_id, SUB_COUNT)
        say(f"seed pass: created={created} existing={existing} total={created + existing} "
            f"in {wall:.2f}s ({(created + existing) / wall:.0f}/s)")
        total = list_total(admin, list_id)
    check(total >= SUB_COUNT,
          f"list {MAIN_LIST!r} id={list_id} holds {total} subscribers (real-time count)")
    # Real-time subscribed baseline (subscribers not unsubscribed) via a live query.
    unsub_before = admin.query_subscribers(list_id, "unsubscribed", per_page=1)[2]
    subbed = total - unsub_before
    template_id = admin.get_default_template_id()
    say(f"seeded={total} subscribed(not-unsubscribed)={subbed}; default campaign template id={template_id}")

    # ---------------------------------------------------------------- PHASE 1
    phase("PHASE 1 — CAMPAIGN -> SINK (presence: delivered vs subscriber count)")
    subj1 = f"F1 Bench Campaign One [{RUN}]"
    q1 = f'subject:"{subj1}"'
    cp1 = sink.checkpoint(q1)
    camp1 = run_campaign(admin, f"f1-camp1-{RUN}", subj1, list_id, template_id)
    record("campaign #1", f"campaign #1 started (id={camp1['id']}) to list {list_id}")

    c1 = wait_campaign_finished(admin, camp1["id"])
    to_send1, sent1 = c1.get("to_send"), c1.get("sent")
    say(f"campaign #1 FINISHED: to_send={to_send1} sent={sent1} "
        f"(to_send is listmonk's real-time recipient query, not the mat view)")
    delivered1 = wait_count(sink, q1, target=sent1) - cp1[1]
    check(to_send1 == subbed,
          f"listmonk to_send ({to_send1}) == subscribed subscriber count ({subbed})")
    check(sent1 == to_send1, f"listmonk sent ({sent1}) == to_send ({to_send1}) — 0 send errors")
    check(delivered1 == sent1,
          f"sink delivered ({delivered1}) == listmonk sent ({sent1}) — full-list presence")
    record("campaign #1", f"{delivered1}/{subbed} campaign #1 messages captured in sink")

    # ---------------------------------------------------------------- PHASE 2
    phase("PHASE 2 — UNSUBSCRIBE ROUND-TRIP (criterion-shaped)")
    # Pick a still-subscribed member deterministically (first by id).
    st, results, tot = admin.query_subscribers(list_id, "confirmed", per_page=1)
    if not results:
        st, results, tot = admin.query_subscribers(list_id, "unconfirmed", per_page=1)
    check(bool(results), "found a still-subscribed member to unsubscribe")
    target = results[0]
    addr = target["email"]
    say(f"unsubscribe target: {addr} (subscriber id={target['id']})")

    # Fetch THEIR actual campaign email from the sink and extract the unsub URL.
    msgs = sink.search(f"to:{addr}", limit=5)
    check(bool(msgs), f"target's campaign email present in sink (to:{addr})")
    full = sink.message(msgs[0]["ID"])
    blob = (full.get("HTML") or "") + "\n" + (full.get("Text") or "")
    m = UNSUB_RE.search(blob)
    check(bool(m), "extracted {{ UnsubscribeURL }} from the captured email body")
    unsub_url = m.group(0)
    say(f"unsubscribe URL from email: {unsub_url}")

    # Follow what the page requires: GET renders the unsubscribe form; the simple
    # unsubscribe is a POST to the same URL (no manage field, no nonce).
    gst, page = http_get(unsub_url)
    check(gst == 200 and "unsub-form" in page,
          f"GET unsubscribe page -> HTTP {gst}, renders the unsubscribe form")
    pst, presult = http_post_form(unsub_url, {})   # empty body -> simple unsubscribe from campaign's list
    check(pst == 200, f"POST unsubscribe -> HTTP {pst} (mechanism: form POST, empty body)")
    record("unsubscribe", f"{addr} completed unsubscribe over plain HTTP (POST form)")

    # Verify via the admin API that the list subscription is now `unsubscribed`.
    st, sub = admin.get_subscriber(target["id"])
    status_for_list = None
    for l in (sub or {}).get("lists", []):
        if l.get("id") == list_id:
            status_for_list = l.get("subscription_status")
    check(status_for_list == "unsubscribed",
          f"admin API confirms subscription_status == 'unsubscribed' (was {status_for_list!r})")
    record("unsubscribe", f"admin API: {addr} subscription_status=unsubscribed on list {list_id}")

    # ---------------------------------------------------------------- PHASE 3
    phase("PHASE 3 — PER-ADDRESS ABSENCE (presence + absence in one window)")
    # Absence checkpoint scoped to the unsubscribed address (baseline includes
    # its 1 campaign-#1 message).
    cp_absent = sink.checkpoint(f"to:{addr}")
    say(f"absence checkpoint on to:{addr} (baseline={cp_absent[1]} — its campaign #1 mail)")

    subj2 = f"F1 Bench Campaign Two [{RUN}]"
    q2 = f'subject:"{subj2}"'
    cp2 = sink.checkpoint(q2)
    camp2 = run_campaign(admin, f"f1-camp2-{RUN}", subj2, list_id, template_id)
    record("campaign #2", f"campaign #2 started (id={camp2['id']}) to same list after unsubscribe")

    c2 = wait_campaign_finished(admin, camp2["id"])
    to_send2, sent2 = c2.get("to_send"), c2.get("sent")
    subbed2 = to_send2
    say(f"campaign #2 FINISHED: to_send={to_send2} sent={sent2} (real-time recipient query)")
    delivered2 = wait_count(sink, q2, target=sent2) - cp2[1]

    # (a) PRESENCE — the still-subscribed cohort received campaign #2. The
    # unsubscribed member is excluded by listmonk's own recipient query, so
    # to_send drops by exactly one.
    check(to_send2 == to_send1 - 1,
          f"exactly one fewer recipient after the unsubscribe ({to_send1} -> {to_send2})")
    check(delivered2 == sent2 == to_send2,
          f"sink delivered ({delivered2}) == sent ({sent2}) == still-subscribed ({to_send2}) — presence")
    record("campaign #2", f"{delivered2}/{to_send2} campaign #2 messages captured (presence)")

    # (b) ABSENCE — the unsubscribed address received NOTHING new. The second
    # campaign has FINISHED (event), so no mail is queued-but-unsent: the window
    # is closed and the absence is sound.
    say(f"asserting NO campaign #2 mail reached the unsubscribed address {addr} ...")
    sink.assert_none_new(cp_absent, settle=3.0)
    # Belt-and-suspenders: campaign #2 subject was never delivered to that address.
    cross = sink.count(f'to:{addr} subject:"{subj2}"')
    check(cross == 0, f"no campaign #2 message addressed to {addr} (cross-check count={cross})")
    check(True, f"per-address absence holds: 0 new messages to {addr} across campaign #2 "
                f"[query used: to:{addr}]")
    record("campaign #2", f"absence verified: 0 new to {addr} (query 'to:{addr}')")

    # ---------------------------------------------------------------- PHASE 4
    phase("PHASE 4 — double opt-in variant (optional)")
    optin_result = "skipped"
    try:
        olist = ensure_list(admin, OPTIN_LIST, optin="double")
        oaddr = f"optin-{RUN}@{seed.SUB_DOMAIN}"
        cp_optin = sink.checkpoint(f"to:{oaddr}")
        st, osub = admin.create_subscriber(oaddr, f"Optin {RUN}", [olist["id"]], preconfirm=False)
        check(st in (200, 201) and isinstance(osub, dict),
              f"created double-opt-in subscriber {oaddr} (status unconfirmed)")
        # Auto opt-in mail should fire; if not, trigger it explicitly.
        try:
            confirm_mail = sink.wait_new(cp_optin, timeout=20)
        except TimeoutError:
            say("no auto opt-in mail; triggering POST /api/subscribers/{id}/optin")
            admin.req("POST", f"/api/subscribers/{osub['id']}/optin")
            confirm_mail = sink.wait_new(cp_optin, timeout=20)
        check(bool(confirm_mail), "double opt-in confirmation mail captured in sink")
        full = sink.message(confirm_mail["ID"])
        blob = (full.get("HTML") or "") + "\n" + (full.get("Text") or "")
        mo = OPTIN_RE.search(blob)
        check(bool(mo), "extracted opt-in confirm URL from the captured mail")
        # Confirm over plain HTTP (POST confirm=true).
        confirm_url = mo.group(0)
        cst, _ = http_post_form(confirm_url, {"confirm": "true"})
        check(cst == 200, f"POST opt-in confirm -> HTTP {cst}")
        st, osub2 = admin.get_subscriber(osub["id"])
        ost = None
        for l in (osub2 or {}).get("lists", []):
            if l.get("id") == olist["id"]:
                ost = l.get("subscription_status")
        check(ost == "confirmed", f"opt-in state flipped to 'confirmed' (was {ost!r})")
        record("opt-in", f"{oaddr}: unconfirmed -> confirmation mail -> confirmed")
        optin_result = "done"
    except (DemoError, TimeoutError, AssertionError, KeyError) as e:
        say(f"opt-in variant skipped (F1 follow-up): {type(e).__name__}: {e}")
        optin_result = "skipped"

    # ---------------------------------------------------------------- PHASE 5
    phase("PHASE 5 — timeline")
    print(f"{'STAGE':<24}{'WALL':>8}  EVENT", flush=True)
    print("-" * 74, flush=True)
    for stage, w, desc in TIMELINE:
        print(f"{stage:<24}{w:>8}  {desc}", flush=True)

    phase("RESULT — messaging-capture + seeding + per-address absence proven")
    for line in (
        f"  seed              : {total} subscribers on {MAIN_LIST!r}",
        f"  campaign #1 -> sink: {delivered1}/{subbed} delivered (full-list presence)",
        f"  unsubscribe RT    : {addr} -> POST unsub form -> API status 'unsubscribed'",
        f"  campaign #2       : presence {delivered2}/{subbed2} + ABSENCE 0 to {addr}",
        f"  double opt-in     : {optin_result}",
    ):
        print(line, flush=True)
    say(f"ALL ASSERTIONS PASSED in {time.monotonic() - _t0:.1f}s wall time")


if __name__ == "__main__":
    try:
        main()
    except (DemoError, TimeoutError, AssertionError) as e:
        print(f"\n[{_wall()}] FAIL  {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
