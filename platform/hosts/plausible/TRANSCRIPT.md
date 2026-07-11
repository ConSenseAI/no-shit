# noshit-f1-plausible — captured run

Real run on the F1 bench host, 2026-07-11. Cold `./demo.sh --reset` exited **0**;
a warm `./demo.sh` re-run also exited 0. Stack DOWN at end; durable Postgres +
ClickHouse state preserved under `/home/user/fixture-runtime/plausible/`.

## Disk gates (image pulls)

Budget ≤ 1.8 GB new pulls; hard floor 1.5 GiB; `df -h /` gate before each pull.

```
start of leg                        6.6 GiB avail
gate #1  (before postgres:16-alpine) 6.6 GiB avail  -> pull ok (alpine base shared with pg15)
gate #2  (before plausible CE)       6.3 GiB avail  -> pull ok
gate #3  (before clickhouse, HARD)   6.2 GiB (6249 MiB) avail  -> 4713 MiB above floor -> pull ok
after all three pulls                5.6 GiB avail  ->  ~1.0 GiB total new-pull footprint (< 1.8 GB)
after cold + warm demo runs          4.4 GiB avail  (DB data ~75 MB; the rest is the parallel build)
```

## Images pulled (digest-pinned)

```
ghcr.io/plausible/community-edition:v3.2.1   167 MB  sha256:33e60bfb40f2df5da00f8753b76fad04f67dba3abe6d73eb516e440e3fb62985
clickhouse/clickhouse-server:24.12-alpine    560 MB  sha256:cd450891db46cc6ffe313ca2b0fb7dbfb897a6873ca74a724cbe050a2cf62621
postgres:16-alpine                           294 MB  sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777
axllent/mailpit:v1.30.4 (REUSED, resident)    34 MB  sha256:5a49a77c5bdbe7c5474450b4f46348d09949df3695257729c93a30369382d4f6
```

Runtime image libc confirmed **Alpine 3.22 / musl** (`/lib/libc.musl-x86_64.so.1`),
runtime user **uid 999** — both load-bearing (deviations D1/D2, F2 clock note).

## Cold run — `./demo.sh --reset` (exit 0)

### setup + cold first-boot (health-gated, no sleep-as-sync)
```
[demo] setup (secrets + durable dirs + images) ...
== noshit-f1-plausible — setup ==
[ok] durable data dirs under: /home/user/fixture-runtime/plausible
[ok] image present (reused): mailpit
[ok] image present: postgres (pinned by digest)
[ok] image present: clickhouse (pinned by digest)
[ok] image present: plausible (pinned by digest)
[demo] --reset: wiping durable data at /home/user/fixture-runtime/plausible ...
[demo] starting stack (up -d --wait; first boot migrates PG + CH + warms caches, be patient) ...
 Container noshit-f1-plausible-clickhouse-1 Healthy
 Container noshit-f1-plausible-db-1 Healthy
 Container noshit-f1-plausible-plausible-1 Started
 Container noshit-f1-plausible-mailpit-1 Healthy
 Container noshit-f1-plausible-plausible-1 Healthy
[demo] stack healthy.
```
(First-EVER boot on a cold OS page cache took several minutes — migrations + full
cache warm before the HTTP endpoint accepted connections. This --reset boot, with
image layers already in page cache, was ~28 s.)

### seed — bootstrap founder + site + bulk event pass
```
[seed] fresh instance: registering founder founder@fixture.test (LiveView WS register -> activation-code round-trip) ...
[seed] founder registered + activated (code round-trip ok, code=8297)
[seed] created site bench.fixture.test (POST /sites, classic HTTP)
[seed] bulk pass: firing 500 pageviews + 24 custom events at POST /api/event ...
[seed] ingestion-cache readiness: site became ingestible ~24.1s after creation (events dropped until then)
[seed] SENT 524 events (500 pageviews) in 1.27s (413 events/s); accepted=524 dropped=0
[seed] ClickHouse buffered-visibility: dashboard pageviews converged 0 -> 500 (+500) in ~4.2s after the send pass
[seed] readback verified: dashboard Total pageviews=500 (>= baseline 0 + 500 sent), Unique visitors=11
```

**Ingest wall-time:** 524 events (500 pageviews + 24 custom) in **1.27 s ≈ 413
events/s**, **0 dropped**. Two async-visibility latencies observed and handled by
polling (not timers): site-cache ingestion readiness **~24.1 s** (fresh site) and
ClickHouse buffered readback convergence **~4.2 s** (pageviews 0 → 500).
Unique visitors = 11 (10 virtual visitors + the 1 accepted `cache_probe`).

### proof — `demo.py` (all phases PASS, 11.8 s)
```
== PHASE 1 — REGISTRATION MAIL ROUND-TRIP (fresh user, verification ON)
[   1.1s] PASS  activation email present in sink for demo-1783755863@fixture.test (count=1);
                4-digit code 3402 extracted from the REAL body and submitted to /activate
[   1.2s] PASS  authenticated GET /sites -> HTTP 200 (activation succeeded; session authorizes real reads)

== PHASE 2 — SITE + INGEST + READBACK via the REAL /api/event path (§2.3)
[   4.7s] PASS  0 events dropped at POST /api/event (all 524 accepted, x-plausible-dropped absent)
[   4.7s] PASS  ClickHouse buffered visibility: dashboard pageviews converged to 1000 (+500) ~2.1s after send
[   4.7s] PASS  readback EQUALS sent: dashboard Total pageviews 1000 == baseline 500 + 500 sent

== PHASE 3 — PRESENCE + ABSENCE PAIR (event-anchored, FIXTURES §2.2)
[   4.7s] anchor = activation-COMPLETED event for the fresh user (PHASE 1), NOT a timer
[   7.8s] PASS  control address control-1783755863@fixture.test received 0 mail (never targeted) — census-wide absence
[  11.8s] PASS  no residual mail to demo-1783755863@fixture.test after activation settled (still 1) — per-address absence

[  11.8s] ALL ASSERTIONS PASSED in 11.8s wall time
```

**Sink evidence (msg-channel census, via `harness/mailsink.py`):**
- Activation email captured for the fresh user; subject `"<code> is your Plausible
  email verification code"`; the 4-digit code (e.g. `3402`) was extracted from the
  **real body** and POSTed to `/activate` — round-trip closed.
- Absence pair anchored on the activation-completed event: **0** messages to the
  never-touched control address (census-wide), and the registered user held
  **exactly 1** message (the activation email) with **no residual** after settle.

### timings + teardown
```
[demo] seed  : 32s   (dominated by the ~24s site-cache ingestion-readiness wait on the fresh site)
[demo] proof : 11s
[demo] total : 73s   (incl. up / seed / proof / teardown)
[demo] demo.py exit code: 0
[demo] tearing down (scoped: noshit-f1-plausible down; durable data preserved) ...
=== EXIT: 0 ===
```

## Warm re-run — `./demo.sh` (exit 0)

Durable Postgres + ClickHouse reused; founder logged in idempotently; a fresh
per-run unique user drives PHASE 1, so warm re-runs stay green:
```
[seed] warm start: logged in as founder@fixture.test
[seed] ingestion-cache readiness: site became ingestible ~0.0s after creation   (site already cached)
[seed] readback verified: dashboard Total pageviews=1500 (>= baseline 1000 + 500 sent), Unique visitors=11
  registration RT   : demo-1783755968@fixture.test -> WS register -> activation code 9178 in sink -> /activate -> authed GET /sites 200
  ingest + readback : 500 pageviews via POST /api/event -> dashboard Total pageviews 1500->2000 (==sent; converge ~3.1s)
[  12.9s] ALL ASSERTIONS PASSED in 12.9s wall time
[demo] seed  : 5s   [demo] proof : 13s   [demo] total : 35s   [demo] demo.py exit code: 0
```
Delta-based readback across runs: dashboard pageviews `0 → 500 → 1000 → 1500 →
2000` — each `+500` pass equals what was sent. Warm site-cache readiness ~0 s
(vs ~24 s cold) confirms the caveat is site-cache propagation, not a fixed cost.

## F2 clock note (printed by `demo.py` PHASE 4 — orientation, no proof)

- **libc:** Alpine 3.22 / musl → F2 rung-2 uses the **glibc-sidecar libfaketime**
  pattern (not a direct musl `LD_PRELOAD`).
- **scheduled work:** Oban cron in the BEAM (CE `base_cron` only), **enumerable +
  harness-triggerable** via `bin/plausible rpc … Oban.insert()` / `…perform(…)`;
  `DISABLE_CRON=true` is a clean rung-3 off-switch.
- **native clock targets:** `ScheduleEmailReports` (weekly/monthly report emails),
  `TrafficChangeNotifier` (spike/drop notifications), `SendSiteSetupEmails` /
  `SendCheckStatsEmails` (onboarding drip) — the longitudinal messaging the
  virtual clock compresses.

## End state
```
running containers (project): none  (stack DOWN)
durable state:  db 66M · clickhouse 8.4M · seed-state.json (0600) · captures (empty)
secrets:        .env 0600 · seed-state.json 0600  (both gitignored)
```
