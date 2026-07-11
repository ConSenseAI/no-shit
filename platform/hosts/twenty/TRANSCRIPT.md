# TRANSCRIPT — noshit-f1-twenty

Verbatim capture of one successful **pristine cold-start** run of the Twenty CRM
F1 bench leg. Pristine = the durable DB wiped first so Twenty runs its fresh-DB
init from nothing and the first workspace is created through Twenty's own signup:

    ./demo.sh --reset            # wipe -> up --wait -> seed -> proof -> down

**Result:** all assertions passed, `demo.py` exit code 0. Run **twice** back-to-back
from cold (coordinator-style independent re-run), green both times.
**Seed:** 230 records created in **0.64 s** (361/s) — 115 companies + 115 people in
one deterministic batched pass (a fresh workspace ships ~5 sample companies + ~5
sample people, so totals land at 120 / 120; see README deviation #6).
**Proof wall time (`demo.py`):** 13.6 s. **Total incl. up/seed/teardown:** 129 s
(dominated by Twenty's first-boot migrations + metadata provisioning).
**Captured:** 2026-07-11.
**Host:** Docker via `sg docker`; compose project `noshit-f1-twenty`; loopback-only ports.
**Images:** twentycrm/twenty:v2.20.0 (1.12 GB on disk, new pull), postgres:16-alpine
(294 MB, new pull), redis:7-alpine (39 MB, new pull), axllent/mailpit:v1.30.4
(34 MB, reused).

Record counts are cross-checked two ways: Twenty's own `companies/people
{ totalCount }` (GraphQL data API) and `GET /rest/companies` `totalCount` (REST).
The messaging proof drives a real **workspace-member invite** (`sendInvitations`)
into the Mailpit sink; the per-address absence is asserted only **after** the
invite has been **delivered** (`harness/mailsink.py` `wait_new` returned — an
event, not a timer), so no mail is queued-but-unsent when the window closes.

```text
[demo] setup (secrets + durable dirs + images) ...
== noshit-f1-twenty — setup ==
[ok] durable data dirs under: /home/user/fixture-runtime/twenty
[ok] .env exists — keeping it (pass --force to regenerate)
[ok] image present (reused): postgres:16-alpine
[ok] image present (reused): redis:7-alpine
[ok] image present (reused): axllent/mailpit:v1.30.4
[ok] image present: twenty (pinned by digest)
== setup complete — run ./demo.sh ==
[demo] --reset: wiping durable data at /home/user/fixture-runtime/twenty ...
[demo] cold start: clearing any prior containers (data preserved) ...
[demo] starting stack (up -d --wait; first boot migrates, be patient) ...
 (compose creates network + db/redis/mailpit/server/worker; waits on healthchecks)
 Container noshit-f1-twenty-db-1       Healthy
 Container noshit-f1-twenty-redis-1    Healthy
 Container noshit-f1-twenty-mailpit-1  Healthy
 Container noshit-f1-twenty-server-1   Healthy
 Container noshit-f1-twenty-worker-1   Healthy
[demo] stack healthy.
[demo] seeding (idempotent) ...
[seed] waiting for Twenty at http://localhost:3001 ...
[seed] fresh instance: signing up the founder + first workspace ...
[seed] workspace created + activated (id=a2f6e955-b8ea-43e3-ac91-056303dd3b13)
[seed] companies: created=115 total=120 in 0.30s
[seed] people:    created=115 total=120 in 0.34s
[seed] BULK PASS: 230 records created in 0.64s (361/s)
[seed] API key minted + used: REST /rest/companies read -> HTTP 200, totalCount=120
[seed] verified totals: companies=120 people=120
[demo] running E2 + messaging proof ...

==========================================================================
== PHASE 0 — preflight (sink, Twenty, founder state, seed)
==========================================================================
[   0.0s] sink reachable at http://localhost:8030 (0 message(s) held)
[   0.5s] PASS  founder state present (email=founder@fixture.test)

==========================================================================
== PHASE 1 — USER-PATH ENTRY (login over HTTP -> authenticated API read)
==========================================================================
[   0.6s] TIMELINE  login                founder@fixture.test logged in via /metadata auth endpoints (HTTP)
[   0.7s] PASS  authenticated GraphQL read: companies.totalCount=120 (>= 120 seeded)
[   0.7s] PASS  authenticated GraphQL read: people.totalCount=120 (>= 120 seeded)
[   0.7s] PASS  authenticated REST read: GET /rest/companies -> HTTP 200, totalCount=120
[   0.7s] TIMELINE  read                 token authorizes real reads (GraphQL 120 companies / 120 people; REST 200)
[   0.7s] PASS  resolved a workspace role id for the invite

==========================================================================
== PHASE 2 — MAIL -> SINK PRESENCE (workspace invite -> captured email)
==========================================================================
[   0.9s] PASS  sendInvitations returned success for invitee-1783741517@fixture.test
[   0.9s] TIMELINE  invite               invite sent to invitee-1783741517@fixture.test (role id=483f2cec-d36b-4f45-bb33-e1c45dd807ef)
[   6.4s] TIMELINE  invite               invite email captured in sink (to:invitee-1783741517@fixture.test)
[   6.4s] PASS  captured message is addressed to invitee-1783741517@fixture.test (To=['invitee-1783741517@fixture.test'])
[   6.4s] PASS  subject matches an invite: 'Join your team on Twenty'
[   6.4s] PASS  captured email carries an /invite/... link with an inviteToken
[   6.4s] PASS  emailed link targets http://localhost:3001 (SERVER_URL correct): http://localhost:3001/invite/a3ba9ec5-ffb8-4e64-aefb-397bd7b2ed2b?invite...
[   6.4s] TIMELINE  invite               link -> http://localhost:3001/invite/a3ba9ec5-ffb8-4e64-aefb-397bd7b... (host-reachable, SERVER_URL correct)

==========================================================================
== PHASE 3 — EVENT-ANCHORED ABSENCE (residual-messaging shape)
==========================================================================
[   6.4s] anchor = invite delivered (PHASE 2 event); settle window covers transport latency only
[   9.4s] PASS  control address control-1783741517@fixture.test received 0 mail (never targeted) — absence holds
[   9.4s] TIMELINE  absence              0 mail to never-invited control-1783741517@fixture.test (anchored on invite-delivered)
[  13.4s] PASS  exactly 1 message to invitee-1783741517@fixture.test — no residual/duplicate mail after the invite (count=1)
[  13.4s] TIMELINE  absence              no residual mail to invitee-1783741517@fixture.test after its single invite (still 1)

==========================================================================
== PHASE 4 — CSV export via REST (optional nli bonus)
==========================================================================
[  13.6s] PASS  CSV export enumerated all 120 companies (== REST totalCount 120)
[  13.6s] PASS  exported 120 rows to /home/user/fixture-runtime/twenty/captures/companies-1783741517.csv (>= 120 seeded)
[  13.6s] TIMELINE  export               120 companies -> /home/user/fixture-runtime/twenty/captures/companies-1783741517.csv (2 REST pages)

==========================================================================
== PHASE 5 — timeline
==========================================================================
STAGE                     WALL  EVENT
--------------------------------------------------------------------------
login                     0.6s  founder@fixture.test logged in via /metadata auth endpoints (HTTP)
read                      0.7s  token authorizes real reads (GraphQL 120 companies / 120 people; REST 200)
invite                    0.9s  invite sent to invitee-1783741517@fixture.test (role id=483f2cec-d36b-4f45-bb33-e1c45dd807ef)
invite                    6.4s  invite email captured in sink (to:invitee-1783741517@fixture.test)
invite                    6.4s  link -> http://localhost:3001/invite/a3ba9ec5-ffb8-4e64-aefb-397bd7b... (host-reachable, SERVER_URL correct)
absence                   9.4s  0 mail to never-invited control-1783741517@fixture.test (anchored on invite-delivered)
absence                  13.4s  no residual mail to invitee-1783741517@fixture.test after its single invite (still 1)
export                   13.6s  120 companies -> /home/user/fixture-runtime/twenty/captures/companies-1783741517.csv (2 REST pages)

==========================================================================
== RESULT — host bring-up + seeding + messaging capture + absence proven
==========================================================================
  user-path entry   : founder@fixture.test login -> token -> real API read (GraphQL + REST)
  seed present      : 120 companies + 120 people (>= 120/120)
  mail -> sink      : workspace invite to invitee-1783741517@fixture.test captured; link -> http://localhost:3001/invite/...
  absence (anchored): 0 to control control-1783741517@fixture.test; no residual to invitee-1783741517@fixture.test (anchor: invite-delivered)
  CSV export (bonus): 120 rows
[  13.6s] ALL ASSERTIONS PASSED in 13.6s wall time

[demo] --- timings ---------------------------------------------
[demo] seed  : 7s (record-creation wall-time is in seed output)
[demo] proof : 14s (demo.py)
[demo] total : 129s (incl. up/seed/proof/teardown)
[demo] demo.py exit code: 0
[demo] reset path: rm -rf /home/user/fixture-runtime/twenty/*   (or ./demo.sh --reset)

[demo] tearing down (scoped: noshit-f1-twenty down; durable data preserved) ...
 (worker/server/redis/mailpit/db stopped + removed, network removed; the
  bind-mounted Postgres data + server storage under
  /home/user/fixture-runtime/twenty/ survive)
```

## What the sink held (the msg-channel census for this run)

- **1** workspace-member invite message, subject **"Join your team on Twenty"**,
  to `invitee-<run>@fixture.test`, carrying a host-reachable join link
  `http://localhost:3001/invite/<workspaceInviteHash>?inviteToken=<token>` — the
  presence half (SERVER_URL correctness proven: the link targets the
  host-published origin, not the container-internal one).
- **0** messages to `control-<run>@fixture.test` (never invited) and **no second
  message** to the invited address after its single invite — the absence half,
  anchored on the invite-**delivered** event. This presence+absence pair in one
  script window is the residual-messaging shape a clean nli verdict is made of
  (FIXTURES §2.2 / O-2).

## Clock-story note (recorded for F2, not proven here)

The `twentycrm/twenty:v2.20.0` image is **musl / Alpine** (`node:24.18.0-alpine3.23`,
Node 24, uid 1000) — so it needs the **glibc-sidecar** libfaketime pattern (as the
`documenso` F0 leg used), not a straight rung-2 `LD_PRELOAD`. Twenty's **worker**
container (`yarn worker:prod`, BullMQ over Redis `noeviction`) is where async /
scheduled jobs execute — **that is the process a fake clock must reach**; the
server only registers the cron schedules.
```
