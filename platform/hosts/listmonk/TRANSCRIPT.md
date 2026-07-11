# TRANSCRIPT — noshit-f1-listmonk

Verbatim capture of one successful **pristine cold-start** run of the Listmonk
F1 bench leg. Pristine = the durable DB wiped first so listmonk installs from
nothing:

    ./demo.sh --reset            # wipe DB -> up --wait -> seed -> proof -> down

**Result:** all assertions passed, `demo.py` exit code 0.
**Seed:** 200 subscribers registered in **1.19 s** (168/s), one deterministic pass.
**Proof wall time (`demo.py`):** 10.5 s. **Total incl. up/seed/teardown:** 33 s.
**Captured:** 2026-07-11.
**Host:** Docker via `sg docker`; compose project `noshit-f1-listmonk`; loopback-only ports.
**Images:** listmonk/listmonk:v6.2.0 (32 MB, the only new pull), postgres:15-alpine
(292 MB, reused), axllent/mailpit:v1.30.4 (34 MB, reused).

Delivery counts are cross-checked two ways: listmonk's own `to_send`/`sent`
(a real-time recipient query) and an independent count in the Mailpit sink via
`harness/mailsink.py`. The per-address absence is asserted only after the second
campaign has **FINISHED** (an event, not a timer), so no mail is
queued-but-unsent when the window closes.

```text
[demo] setup (secrets + durable dir + images) ...
== noshit-f1-listmonk — setup ==
[ok] durable data dir: /home/user/fixture-runtime/listmonk/db
[ok] .env exists — keeping it (pass --force to regenerate)
[ok] image present (reused): postgres:15-alpine
[ok] image present (reused): axllent/mailpit:v1.30.4
[ok] image present: listmonk (pinned)
== setup complete — run ./demo.sh ==
[demo] --reset: wiping durable DB at /home/user/fixture-runtime/listmonk ...
[demo] cold start: clearing any prior containers (data preserved) ...
[demo] starting stack (up -d --wait) ...
 (compose creates network + db/mailpit/app; waits on healthchecks)
 Container noshit-f1-listmonk-db-1       Healthy
 Container noshit-f1-listmonk-mailpit-1  Healthy
 Container noshit-f1-listmonk-app-1      Healthy
[demo] stack healthy.
[demo] seeding (idempotent) ...
[seed] waiting for listmonk at http://localhost:9002 ...
[seed] logged in as Super Admin
[seed] pointing SMTP at mailpit:1025, root_url=http://localhost:9002 ...
[seed] messaging configured (settings reload converged)
[seed] list ready: 'F1 Fixture List' id=3 uuid=0626c579-6af2-409d-bdab-aaee1fdf6a8a
[seed] subscribers: created=200 existing=0 total=200 in 1.19s (168/s)
[seed] list now holds subscriber_count=0 statuses={}      <-- stale mat view; real count is 200 (see README finding #3)
[demo] running E2 proof ...

==========================================================================
== PHASE 0 — preflight (sink, listmonk, admin, seed)
==========================================================================
[   0.0s] sink reachable at http://localhost:8029 (0 message(s) held)
[   0.1s] listmonk healthy at http://localhost:9002; logged in as Super Admin
[   0.1s] messaging -> sink confirmed (SMTP mailpit:1025, root_url=http://localhost:9002)
[   0.2s] PASS  list 'F1 Fixture List' id=3 holds 200 subscribers (real-time count)
[   0.2s] seeded=200 subscribed(not-unsubscribed)=200; default campaign template id=1

==========================================================================
== PHASE 1 — CAMPAIGN -> SINK (presence: delivered vs subscriber count)
==========================================================================
[   0.2s] TIMELINE  campaign #1            campaign #1 started (id=2) to list 3
[   2.2s] campaign #1 FINISHED: to_send=200 sent=200 (to_send is listmonk's real-time recipient query, not the mat view)
[   2.3s] PASS  listmonk to_send (200) == subscribed subscriber count (200)
[   2.3s] PASS  listmonk sent (200) == to_send (200) — 0 send errors
[   2.3s] PASS  sink delivered (200) == listmonk sent (200) — full-list presence
[   2.3s] TIMELINE  campaign #1            200/200 campaign #1 messages captured in sink

==========================================================================
== PHASE 2 — UNSUBSCRIBE ROUND-TRIP (criterion-shaped)
==========================================================================
[   2.3s] PASS  found a still-subscribed member to unsubscribe
[   2.3s] unsubscribe target: member-200@fixture.test (subscriber id=202)
[   2.3s] PASS  target's campaign email present in sink (to:member-200@fixture.test)
[   2.3s] PASS  extracted {{ UnsubscribeURL }} from the captured email body
[   2.3s] unsubscribe URL from email: http://localhost:9002/subscription/b229ab3a-324f-454d-9543-27ec41039bbd/e812f732-dac0-4e9c-9be1-4c72f51f88dc
[   2.3s] PASS  GET unsubscribe page -> HTTP 200, renders the unsubscribe form
[   2.3s] PASS  POST unsubscribe -> HTTP 200 (mechanism: form POST, empty body)
[   2.3s] TIMELINE  unsubscribe            member-200@fixture.test completed unsubscribe over plain HTTP (POST form)
[   2.3s] PASS  admin API confirms subscription_status == 'unsubscribed' (was 'unsubscribed')
[   2.3s] TIMELINE  unsubscribe            admin API: member-200@fixture.test subscription_status=unsubscribed on list 3

==========================================================================
== PHASE 3 — PER-ADDRESS ABSENCE (presence + absence in one window)
==========================================================================
[   2.3s] absence checkpoint on to:member-200@fixture.test (baseline=1 — its campaign #1 mail)
[   2.3s] TIMELINE  campaign #2            campaign #2 started (id=3) to same list after unsubscribe
[   7.4s] campaign #2 FINISHED: to_send=199 sent=199 (real-time recipient query)
[   7.4s] PASS  exactly one fewer recipient after the unsubscribe (200 -> 199)
[   7.4s] PASS  sink delivered (199) == sent (199) == still-subscribed (199) — presence
[   7.4s] TIMELINE  campaign #2            199/199 campaign #2 messages captured (presence)
[   7.4s] asserting NO campaign #2 mail reached the unsubscribed address member-200@fixture.test ...
[  10.4s] PASS  no campaign #2 message addressed to member-200@fixture.test (cross-check count=0)
[  10.4s] PASS  per-address absence holds: 0 new messages to member-200@fixture.test across campaign #2 [query used: to:member-200@fixture.test]
[  10.4s] TIMELINE  campaign #2            absence verified: 0 new to member-200@fixture.test (query 'to:member-200@fixture.test')

==========================================================================
== PHASE 4 — double opt-in variant (optional)
==========================================================================
[  10.5s] PASS  created double-opt-in subscriber optin-1783735676@fixture.test (status unconfirmed)
[  10.5s] PASS  double opt-in confirmation mail captured in sink
[  10.5s] PASS  extracted opt-in confirm URL from the captured mail
[  10.5s] PASS  POST opt-in confirm -> HTTP 200
[  10.5s] PASS  opt-in state flipped to 'confirmed' (was 'confirmed')
[  10.5s] TIMELINE  opt-in                 optin-1783735676@fixture.test: unconfirmed -> confirmation mail -> confirmed

==========================================================================
== PHASE 5 — timeline
==========================================================================
STAGE                       WALL  EVENT
--------------------------------------------------------------------------
campaign #1                 0.2s  campaign #1 started (id=2) to list 3
campaign #1                 2.3s  200/200 campaign #1 messages captured in sink
unsubscribe                 2.3s  member-200@fixture.test completed unsubscribe over plain HTTP (POST form)
unsubscribe                 2.3s  admin API: member-200@fixture.test subscription_status=unsubscribed on list 3
campaign #2                 2.3s  campaign #2 started (id=3) to same list after unsubscribe
campaign #2                 7.4s  199/199 campaign #2 messages captured (presence)
campaign #2                10.4s  absence verified: 0 new to member-200@fixture.test (query 'to:member-200@fixture.test')
opt-in                     10.5s  optin-1783735676@fixture.test: unconfirmed -> confirmation mail -> confirmed

==========================================================================
== RESULT — messaging-capture + seeding + per-address absence proven
==========================================================================
  seed              : 200 subscribers on 'F1 Fixture List'
  campaign #1 -> sink: 200/200 delivered (full-list presence)
  unsubscribe RT    : member-200@fixture.test -> POST unsub form -> API status 'unsubscribed'
  campaign #2       : presence 199/199 + ABSENCE 0 to member-200@fixture.test
  double opt-in     : done
[  10.5s] ALL ASSERTIONS PASSED in 10.5s wall time

[demo] --- timings ---------------------------------------------
[demo] seed  : 4s (subscriber registration wall-time is in seed output: 1.19s)
[demo] proof : 11s (demo.py)
[demo] total : 33s (incl. up/seed/proof/teardown)
[demo] demo.py exit code: 0
[demo] reset path: rm -rf /home/user/fixture-runtime/listmonk/*   (or ./demo.sh --reset)

[demo] tearing down (scoped: noshit-f1-listmonk down; durable data preserved) ...
 (app/mailpit/db stopped + removed, network removed; the bind-mounted
  Postgres data under /home/user/fixture-runtime/listmonk/ survives)
```

## What the sink held (the msg-channel census for this run)

- **200** campaign-#1 messages (one per subscriber, subject `F1 Bench Campaign One [<run>]`).
- **199** campaign-#2 messages — every still-subscribed member, and **none** to
  `member-200@fixture.test` (the unsubscribed address). This is the presence+absence
  pair, in one script window, that a clean unsubscribe verdict is made of (FIXTURES
  §2.2 / O-2).
- **1** double-opt-in confirmation message to the opt-in subscriber.

The absence query, verbatim: **`to:member-200@fixture.test`** — baseline 1 (its
campaign-#1 mail), still 1 after campaign #2 finished delivering to the other 199.
