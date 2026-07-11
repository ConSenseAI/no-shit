# TRANSCRIPT — noshit-f1-formbricks

Verbatim capture of one successful **pristine cold-start** run of the Formbricks
F1 bench leg. Pristine = the durable DB wiped first so Formbricks runs its
fresh-DB init (128 Prisma migrations against the pgvector image) from nothing and
the founder is created through Formbricks' own signup:

    ./demo.sh --reset            # wipe -> up --wait -> seed -> proof -> down

**Result:** all assertions passed, `demo.py` exit code 0. Verified **cold**
(`--reset`, 363 s) and again **warm** (`./demo.sh`, 32 s) — green both times.
**Seed:** 120 churn responses created in **4.02 s** (30/s) in one deterministic
pass through the public **display→response** API; count verified back via the
management API.
**Proof wall time (`demo.py`):** 10.5 s. **Total incl. up/seed/teardown:** 363 s
(dominated by Formbricks' first-boot migrations).
**Captured:** 2026-07-11.
**Host:** Docker via `sg docker`; compose project `noshit-f1-formbricks`;
loopback-only ports (app 3003, sink 8033/1033). Postgres internal only.
**Disk:** `df -h /` steady at **4.4 GiB avail** before and after the cold run
(the pgvector-enabled Postgres shares the resident `postgres:15-alpine` base — no
second DB image pulled). Floor 1.5 GiB held throughout.
**Images:** `ghcr.io/formbricks/formbricks:v3.16.1` (1.15 GB on disk, new pull,
digest `sha256:1cd324d2dc82eb906bf3a03ffc7d679b81d2d0ebdb35173669a68afe84350239`),
`noshit-f1-formbricks-postgres:15-pgvector` (built local from `postgres:15-alpine`
+ pgvector 0.8.0, ~1 MB unique delta), `axllent/mailpit:v1.30.4` (34 MB, reused).

The response count is cross-checked via Formbricks' management API
(`GET /api/v1/management/responses`). The messaging proofs drive two real mail
flows — the signup **email-verification** mail and the per-response **owner-alert**
mail — into the Mailpit sink; the per-address absence is asserted only **after**
the relevant mail has been **delivered** (`harness/mailsink.py` `wait_new`
returned — an event, not a timer), so nothing is queued-but-unsent when the window
closes.

```text
[demo] setup (secrets + durable dirs + images) ...
== noshit-f1-formbricks — setup ==
[ok] durable data dirs under: /home/user/fixture-runtime/formbricks
[ok] .env exists — keeping it (pass --force to regenerate)
[ok] image present (reused): postgres:15-alpine
[ok] image present (reused): axllent/mailpit:v1.30.4
[ok] image present: formbricks (pinned by digest)
[ok] image present (built): noshit-f1-formbricks-postgres:15-pgvector
== setup complete — run ./demo.sh ==
[demo] --reset: wiping durable data at /home/user/fixture-runtime/formbricks ...
[demo] starting stack (up -d --wait; first boot migrates 128 migrations, be patient) ...
 Container noshit-f1-formbricks-db-1        Healthy
 Container noshit-f1-formbricks-mailpit-1   Healthy
 Container noshit-f1-formbricks-formbricks-1 Healthy
[demo] stack healthy.
[demo] seeding (idempotent: bootstrap + churn survey + >=120 responses) ...
[seed] fresh instance: registering founder via createUser (real signup + verification mail) ...
[seed] org/project/environments created (prod env=cv5vvttpblj4u2ie6842bg1nx)
[seed] management API key minted (sha256) + verified via /management/me
[seed] churn survey created (link survey, inProgress): cmrg3aibm0001t9012mlanmoe
[seed] BULK PASS: 120 churn responses created in 4.02s (30/s) via display->response API
[seed] verified via management API: survey cmrg3aibm0001t9012mlanmoe holds 120 responses (>= 120)
[seed] state -> /home/user/fixture-runtime/formbricks/seed-state.json (0600): founder + org + prod env + api key + survey
[demo] running E2 + messaging proof ...

==========================================================================
== PHASE 0 — preflight (sink, Formbricks, seed state, churn responses)
==========================================================================
[   0.5s] PASS  seed state present (survey=cmrg3aibm0001t9012mlanmoe, env=cv5vvttpblj4u2ie6842bg1nx)
[   0.6s] PASS  seeded churn survey holds 120 responses (>= 120)
[   0.6s] PASS  CRON_SECRET present in env (for the pipeline/notification proof)

==========================================================================
== PHASE 1 — SIGNUP E2 MAIL ROUND-TRIP (fresh user -> verification mail -> follow token)
==========================================================================
[   1.3s] TIMELINE  signup   registered signup-1783757725@fixture.test via createUser server action (plain HTTP)
[   1.3s] PASS  verification mail captured, addressed to signup-1783757725@fixture.test
[   1.3s] PASS  subject is a verification mail: 'Please verify your email to use Formbricks'
[   1.3s] PASS  captured email carries an /auth/verify?token=... link
[   1.3s] PASS  emailed link targets host-reachable http://localhost:3003 (WEBAPP_URL correct): http://localhost:3003/auth/verify?token=eyJhbGciOiJIUzI1NiIsInR5...
[   1.6s] PASS  followed the emailed verify link over plain HTTP -> HTTP 200
[   2.3s] PASS  account active: authenticated NextAuth login succeeded (session user id=cmrg3amc5006qt901cdvj9oq7)

==========================================================================
== PHASE 2 — USER-PATH SURVEY FILL (anonymous churn-survey E2 over plain HTTP)
==========================================================================
[   2.5s] PASS  anonymous GET public survey /s/cmrg3aibm0001t9012mlanmoe -> HTTP 200 (link survey reachable)
[   2.6s] PASS  widget display created (id=cmrg3anki006rt901mcwqnluy)
[   2.6s] PASS  widget response submitted through the public API (id=cmrg3anl1006st901u4czi8qs)
[   2.6s] PASS  response landed: management count 120 -> 121 (+1 via user path)

==========================================================================
== PHASE 3 — NOTIFICATION PRESENCE + ABSENCE PAIR (owner alert via harness pipeline)
==========================================================================
[   2.8s] enabled per-response alert for owner founder@fixture.test on survey cmrg3aibm0001t9012mlanmoe
[   3.5s] PASS  harness-triggered response pipeline (POST /api/pipeline, CRON_SECRET) -> HTTP 200
[   3.5s] PASS  owner alert email captured (presence): subject 'A response for Cancellation / Churn Survey was completed ✅'
[   3.5s] anchor = owner alert delivered (event); settle covers transport latency only
[   6.5s] PASS  control address control-1783757725@fixture.test received 0 mail (never notified) — absence holds
[  10.5s] TIMELINE  notify   no residual/duplicate owner alert after the single pipeline trigger

==========================================================================
== PHASE 5 — timeline
==========================================================================
STAGE                 WALL  EVENT
--------------------------------------------------------------------------
signup                1.3s  registered signup-1783757725@fixture.test via createUser server action (plain HTTP)
signup                1.3s  verification mail in sink (subject 'Please verify your email to use Formbricks')
signup                1.6s  followed emailed verify link (host-reachable, HTTP 200)
signup                2.3s  account verified/active — authenticated login OK (uid=cmrg3amc5006qt901cdvj9oq7)
fill                  2.5s  anonymous end user fetched public survey /s/cmrg3aibm0001t9012mlanmoe
fill                  2.6s  submitted churn response via display->response (id=cmrg3anl1006st901u4czi8qs)
fill                  2.6s  management API confirms the user-path response landed (count 120->121)
notify                3.5s  response pipeline triggered (harness/CRON_SECRET — rung-3 path)
notify                3.5s  owner alert mail in sink (subject 'A response for Cancellation / Churn Survey was completed ✅')
notify                6.5s  0 mail to never-notified control-1783757725@fixture.test (anchored on alert-delivered)
notify               10.5s  no residual/duplicate owner alert after the single pipeline trigger

==========================================================================
== RESULT — churn-survey surface: signup RT + user-path fill + notification pair proven
==========================================================================
  signup RT       : signup-1783757725@fixture.test -> verification mail -> followed emailed token -> login OK
  user-path fill  : anonymous /s/cmrg3aibm0001t9012mlanmoe -> display->response -> landed (count 120->121)
  notification    : owner alert captured (harness pipeline) + absence (0 to control, no residual)
  seed present    : 120 churn responses on the link survey (>= 120)
[  10.5s] ALL ASSERTIONS PASSED in 10.5s wall time

[demo] --- timings ---------------------------------------------
[demo] seed  : 8s (response-creation wall-time is in seed output)
[demo] proof : 10s (demo.py)
[demo] total : 363s (incl. up/seed/proof/teardown)
[demo] demo.py exit code: 0
[demo] tearing down (scoped: noshit-f1-formbricks down; durable data preserved) ...
```

## Warm re-run (idempotent, per-run-unique identities)

```text
[demo] seeding (idempotent: bootstrap + churn survey + >=120 responses) ...
[seed] warm start: founder + api key + survey present (env=cv5vvttpblj4u2ie6842bg1nx)
[seed] idempotent: response target already met, nothing to create
[  11.4s] ALL ASSERTIONS PASSED in 11.4s wall time
[demo] seed  : 1s     proof : 12s     total : 32s     demo.py exit code: 0
```

Warm start reuses the same durable env (`cv5vvttp…`) — the seeded survey +
responses persisted across teardown. `demo.py` uses per-run-unique identities
(`signup-<ts>@`, `control-<ts>@`, a fresh survey response), so the warm run stays
green with no collisions.

## What the sink held (the msg-channel census for the cold run)

- **1** email-verification message from **seed** bootstrap (founder signup), to
  `founder@fixture.test`, subject *"Please verify your email to use Formbricks"*.
- **1** email-verification message from **PHASE 1** (the fresh Proof-1 user), to
  `signup-<run>@fixture.test`, carrying a host-reachable
  `http://localhost:3003/auth/verify?token=<JWT>` link — the presence half of the
  signup round-trip (WEBAPP_URL correctness proven: the link targets the
  host-published origin).
- **1** per-response **owner-alert** message from **PHASE 3**, to
  `founder@fixture.test`, subject *"A response for Cancellation / Churn Survey was
  completed ✅"* — driven by the harness-triggered pipeline (`/api/pipeline`,
  `CRON_SECRET`).
- **0** messages to `control-<run>@fixture.test` (never notified) and **no second
  alert** to the owner after the single pipeline trigger — the absence half,
  anchored on the alert-**delivered** event. This presence+absence pair in one
  script window is the residual-messaging shape a clean nli verdict is made of
  (FIXTURES §2.2 / O-2).

## Clock-story note (recorded for F2, not proven here)

The `ghcr.io/formbricks/formbricks:v3.16.1` image is **musl / Alpine 3.21**
(`node:22`, uid 1001) — so it needs the **glibc-sidecar** libfaketime pattern (as
the `documenso`/`twenty` legs used), not a straight rung-2 `LD_PRELOAD`. Scheduled
work runs via an **in-container `supercronic`** (`/app/docker/cronjobs`, e.g. the
weekly-summary email); per-response owner notifications run through the
**`/api/pipeline`** internal endpoint (self-called via `WEBAPP_URL`, protected by
`CRON_SECRET`). Both are **harness-triggerable** (FIXTURES rung 3) — PHASE 3 drives
the pipeline directly, exactly the shape F2's fake clock will lean on. Native
time-windowed behaviors worth F2 attention: the weekly-summary cadence, survey
scheduling (`status=scheduled` + `runOnDate`), and response recontact windows.
```
