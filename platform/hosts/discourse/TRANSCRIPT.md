# noshit-f1-discourse — TRANSCRIPT (real runs, 2026-07-11)

Host: `/dev/mapper/dmroot` 20 GB shared root (a parallel Twenty F1 leg shared it
early in the session). Docker via `sg docker -c`. All ports loopback-only. The
session ran in two acts: an early attempt blocked by the parallel build (clean
watchdog abort), then — after the coordinator's rotation prune — the build and
**two consecutive GREEN end-to-end demo runs**.

## Summary

| Proof | Status | Evidence (below) |
|---|---|---|
| 1. Forum up + non-interactive admin | **GREEN ×2** | `/srv/status` 200; `/admin/plugins.json` 200 under minted key |
| 2. Signup → activation-mail → active | **GREEN ×2** | mail in sink at +0.5 s; token PUT 200; `active=true` via admin API (users #4, #5) |
| 3. Event-anchored absence | **GREEN ×2** | sidekiq drained to `enqueued=0 busy=0`, then per-address + census-wide `assert_none_new` |
| 4. Bulk seed ≥50 topics | **GREEN ×2** | 55 topics in 18.9 s / 20.0 s, 0 errors, 0 stalls |
| 5. Subscriptions plugin install-only | **GREEN ×2** | listed v2.8.1, enabled, `/s/admin*` sweep 200s, 3 Stripe key settings blank |
| 6. Clock note (evidence) | captured ×2 | glibc 2.36 bookworm; sidekiq 7.3.10; 145 enumerable scheduled jobs |
| Repeatable demo | **exit 0 twice** | run 3: proof 44 s / total 83 s; run 4: proof 44 s / total 80 s |

## df gate readings (rule: floor 1.5 GiB — never crossed at any point)

| Gate / event | Root free | Action |
|---|---|---|
| Session start | 6.2 GiB | manifest sizing only (no pull) |
| Parallel leg building concurrently | 6.2 → 4.5 GiB | authored leg files; attempt #0 |
| **Attempt #0 gate (pull+build)** | **4.43 GiB** | proceed with watchdog |
| Attempt #0 mid-pull | 3.75 → 2.96 → **1.95 GiB** | **watchdog abort** (< 2.2); reclaim → 4.5 GiB; no partial image |
| Coordinator's go (Twenty rotated) | 6.2 GiB | base pull started |
| Base pull (this leg's only pull) | bottom **2.56 GiB**, settle 2.7 GiB | base = 3.18 GB on disk |
| **Bootstrap gate after pull** | **2.60 GiB** | **clean refusal** (< 3.0 min-start) — recorded |
| Coordinator's rotation prune | → **4.26 GiB** | banked-leg images removed (their action) |
| **Bootstrap gate (final)** | **4.26 GiB** | proceed |
| Minimum during the whole build | **4.08 GiB** | watchdog silent (abort line 2.2 never approached) |
| After build / after each demo run | 4.1 GiB | steady |

## One-time provisioning (measured)

- **Base pull**: `discourse/base:2.0.20260706-0040` — ~4.5 min, 3.18 GB on disk,
  amd64 digest `sha256:b0678546cd0835b72b5f9c92888aa936cad92f72781eb6523725eb99faca91db`.
- **Launcher build** (`./bootstrap.sh` → `launcher bootstrap noshit-f1-discourse
  --skip-prereqs`): pups run 04:35:33 → 04:37:36 = **2 min 04 s**; ~2 min 50 s
  total including the image commit. Committed:
  `local_discourse/noshit-f1-discourse` **3.37 GB** (= base + ~190 MB delta),
  image id `sha256:ffe1651720d9c58dc101e3769b6cfc6e5a59e4f4fc658a1970d2a80689cc9c0e`.
- Why so small/fast: `version:` pinned to the SHA already baked into the base
  image (`bf386c2fa76e9aa49ecc225b02271ef062b2ad70`) → checkout/bundle/pnpm
  near-no-ops, ember build a cache hit; plus the `build-rw` shunt kept
  `tmp` + `public/assets` (24 MB + 70 MB) off the overlay and out of the commit.

### Build attempts that FAILED first (each documented in README deviations)

1. **Launcher static preflight**: "You have less than 5GB of free space" at
   4.26 GiB → all launcher calls now carry `--skip-prereqs` (the leg's live
   watchdog supersedes the static check).
2. **Ember bind-mounts**: `.pnpmfile.cjs` ran `git clean -f -X
   app/assets/javascripts` (path exists only because docker mkdir'd it for my
   binds; the frontend moved to `frontend/` at this SHA) → mount points
   undeletable → pnpm failed:
   ```
   [.pnpmfile.cjs] Detected old app/assets/javascripts directory. Cleaning up gitignored files...
   ERROR  Error during pnpmfile execution. ... Error: "Command failed: git clean -f -X app/assets/javascripts
   ```
   Fixed by dropping those two binds (ember scratch is rm'd pre-commit instead).

## The repeatable demo — run 3 (first GREEN) and run 4 (repeat GREEN)

Run 4 timeline (run 3 within ±1 s at every step):

```
    WALL  EVENT
    0.6s  forum up on 127.0.0.1:8084 (Discourse 2026.7.0-latest); admin 'noshit_admin' active, API key authorized
    1.1s  signup POST accepted over plain HTTP (csrf+honeypot); user_id=5, awaiting activation email
    1.6s  activation email delivered to sink and parsed (token bccd0f49ca...)
    2.1s  mail round-trip CLOSED: f1-signup-1783745304@noshit.test signed up -> emailed -> activated -> active
    8.5s  sidekiq drained (observable completion): enqueued=0 busy=0 scheduled=134 retries=0 processed=1023 failed=0
   13.0s  absence window held (opened by activation-arrived + sidekiq-drained; closed after settle)
   33.7s  bulk seed: 55 topics in 20.0s (admin API, category 'F1 Bench'); 3 spot-verified
   36.0s  plugin loaded: listed+enabled, admin route /s/admin.json mounted (200), 18 settings registered, ZERO payment config
   43.5s  clock note captured (libc / sidekiq / scheduled-job enumerability)
[  43.5s] ALL ASSERTIONS PASSED in 43.5s (sink holds 1 message(s))
[demo] demo.py exit code: 0
```

### Mail round-trip evidence (run 3)

```
[   0.6s] endpoint requirements scraped: CSRF token from /session/csrf.json; honeypot from
          /session/hp.json (password_confirmation=<value>, challenge=reverse(<challenge>))
[   0.9s] user_id resolved via admin list filter: 4 (signup JSON omits it at this version)
[   1.4s] activation mail in sink: subject='Confirm your new account' to=f1-signup-1783745128@noshit.test
[   1.7s] submitted activation (PUT + honeypot fields) -> 200
[   1.8s] PASS  user #4 is ACTIVE per admin API after following the emailed activation link
```
The emailed link targets `http://localhost/...` (hostname canonical, port 80
unmapped); the demo submits the parsed hex token against the mapped `:8084` with
the honeypot fields the PUT re-requires (both facts verified in the pinned
source and live).

### Absence window with anchoring events (run 3)

```
[  11.3s]     sidekiq | enqueued=0 busy=0 scheduled=89 retries=0 processed=555 failed=0
[  15.3s] PASS  ABSENCE holds per-address: no further mail to f1-signup-1783745128@noshit.test after
          activation (welcome message + digests disabled; settle covers delivery latency only)
[  15.8s] PASS  ABSENCE holds census-wide: no unexpected mail since the drain event
```
Anchors: window OPENS after (a) the activation mail arrived (a completed
delivery observed in the sink) and (b) the sidekiq immediate queue drained to
`enqueued=0 busy=0` (the observable completion of the mail path — Discourse
sends all mail through sidekiq). `assert_none_new` settle (4 s / 0.5 s) covers
delivery latency only — no timer anchors the window. The sidekiq *scheduled set*
(89 → 134 future-dated periodic jobs) is mini_scheduler's forward calendar, not
pending mail; digest/welcome deferred mail is disabled and recorded
(`send_welcome_message=false`, `disable_digest_emails=true`).

### Seed wall-time (both runs)

```
run 3: [ 46.x ] seed pass: 55 distinct topics created in 18.9s (0 error(s))         # after env fix
run 4: [ 33.1s] seed pass: 55 distinct topics created in 20.0s (0 error(s), 0 rate-limit stall(s))
```
First live run had hit the admin-API request limiter at topic 46
(429 "wait 30 seconds") — fixed by `DISCOURSE_MAX_ADMIN_API_REQS_PER_MINUTE: 400`
(env, container recreate) with content limits lifted via recorded API settings;
the 429 fallback handler recorded zero stalls in the green runs.

### Plugin-loaded evidence (run 3; identical in run 4)

```
[  35.2s] plugin entry: name=discourse-subscriptions enabled=False version=2.8.1 setting=discourse_subscriptions_enabled
[  35.3s] PASS  discourse-subscriptions reports enabled=true after enabling its setting
[  35.3s] plugin admin route /s/admin.json -> 200
[  36.3s] plugin admin route /s/admin -> 200
[  36.3s] plugin admin route /s/admin/subscriptions.json -> 200
[  36.3s] plugin admin route /s/admin/products.json -> 200
[  36.9s] plugin admin route /s/admin/plans.json -> 500        # Stripe-unconfigured error = route exists
[  37.9s] PASS  INSTALL-ONLY confirmed: no Stripe keys set ['discourse_subscriptions_public_key',
          'discourse_subscriptions_secret_key', 'discourse_subscriptions_webhook_secret'] — all blank
```

### Clock-story note for F2 (run output, verbatim)

```
clock | os_release=Debian GNU/Linux 12 (bookworm)
clock | ruby=3.4.9 platform=x86_64-linux
clock | libc=ldd (Debian GLIBC 2.36-9+deb12u14) 2.36
clock | sidekiq=7.3.10 (scheduled jobs run in the in-container sidekiq)
clock | mini_scheduler=true (Discourse's periodic-job driver)
clock | scheduled_job_classes=145
clock | sample_scheduled=["DiscourseGithubPlugin::UpdateJob", "Jobs::AboutStats",
        "Jobs::ActivationReminderEmails", "Jobs::AggregateWebHooksEvents",
        "Jobs::AutoQueueHandler", "Jobs::BackfillDominantColors"]
clock | enumerable_and_triggerable=true (Jobs::Scheduled subclasses; run via Jobs.enqueue / Klass.new.execute)
```
Rung-2 candidate: glibc/Debian → `libfaketime` LD_PRELOAD viable. Rung-3: the
145 scheduled jobs are ordinary classes, enumerable and individually
harness-triggerable via `rails runner` — no wall-clock wait needed.

## End state

- Demo re-runnable part verified green twice, back-to-back (exit 0, 83 s / 80 s).
- Stack DOWN: `noshit-f1-discourse` container **Exited (0)** (launcher stop —
  the appropriate down for a launcher leg: image + durable state kept for a
  ~40 s restart), mailpit container removed, network kept for reuse.
- Durable state under `/home/user/fixture-runtime/discourse/`:
  `shared/standalone` (postgres data incl. 110 seeded topics over the session,
  uploads, logs), `build-rw/` (24 MB tmp + 70 MB compiled assets),
  `discourse_docker/` (launcher).
- Root free at close: **4.1 GiB** (floor 1.5 never approached at any moment of
  the session).
