# noshit-f1-discourse — F1 bench leg (Discourse)

Proves the fixture platform's services on a NEW, heavy host: production-parity
**Discourse** built and run on this machine via the official launcher, the
**signup → activation-email → active** mail round-trip through the leg's Mailpit
sink, an **event-anchored absence** window, **bulk topic seeding** via the admin
API, and the bundled **discourse-subscriptions** plugin **loading** (install-only
— no payments).

Discourse is on the bench because the study's `nst` (subscription-trap) fixtures
implant their diffs in the small MIT `discourse-subscriptions` plugin — the
"cheapest-to-audit diffs" of the build plan. This leg is PUBLIC platform code
(Apache-2.0): **no study fixtures, no labels, no implants, no payment wiring.**

> **Status (2026-07-11): COMPLETE — repeatable proof GREEN twice** (exit 0,
> ~80 s wall each) after a shared-disk saga worth reading: the leg shipped a
> **build-rw shunt** and a **baked-SHA version pin** that together cut the
> launcher build's disk peak from "needs ≥ 5.5 GiB free" to **fits in 4.26 GiB
> with the floor watchdog never firing** (minimum observed free during build:
> 4.08 GiB) and the build wall time from an expected 15–25 min to **~2.5 min**.
> Every resistance met is in the Deviation record. Evidence: `TRANSCRIPT.md`.

## Approach decision: Option A — the official `discourse_docker` launcher

Chosen over Option B (`discourse/discourse_dev`) after measuring both:

| | Option A `discourse_docker` (chosen) | Option B `discourse_dev` |
|---|---|---|
| Base image (amd64, compressed) | `discourse/base` **1.18 GB** (3.18 GB on disk) | `discourse_dev` 1.04 GB |
| Real footprint | base + a **~190 MB** committed delta layer (with this leg's pin+shunt) | image **+ cloned source + gems + node_modules on a bind mount** (~2.3 GB) — larger |
| Production parity | **Yes** — unicorn, nginx, precompiled assets, the canonical deploy | **No** — ember-cli dev server (honesty cost) |
| Plugin model | first-class (subscriptions is bundled-in-core here) | source symlink + restart |
| Non-interactive admin | env + `rails runner` | same runner |

Because Discourse is launcher-managed (not compose), **third-party launcher code
lives OUTSIDE the repo** at `/home/user/fixture-runtime/discourse/discourse_docker`.
This leg dir holds only **our** artifacts: the config template, scripts,
provisioning rails runners, and docs. The launcher forces the container yml to
live in ITS tree (`containers/<name>.yml`) — `setup.sh` renders our committed
template into it (naming constraint: config name == container name ==
`noshit-f1-discourse`).

## Ports (loopback only; registry-allocated)

| Service | Host bind | Notes |
|---|---|---|
| Discourse (nginx) | `127.0.0.1:8084` → container `:80` | launcher `expose` |
| Mailpit UI + REST API | `127.0.0.1:8031` → `:8025` | `harness/mailsink.py` talks here |
| Mailpit SMTP | `127.0.0.1:1031` → `:1025` | parity/debug; the app uses internal `mailpit:1025` |

Postgres + Redis run **inside** the launcher container (bundled) and are **never**
host-published.

## Pins (local build — pins live in config + docs, not a registry digest)

- **Base image**: `discourse/base:2.0.20260706-0040`
  amd64 `@sha256:b0678546cd0835b72b5f9c92888aa936cad92f72781eb6523725eb99faca91db`
  (Debian 12 bookworm / glibc 2.36; the launcher hard-codes this tag)
- **Discourse core**: commit **`bf386c2fa76e9aa49ecc225b02271ef062b2ad70`**
  (main @ 2026-07-06T10:02+10:00 — the EXACT commit baked into the base image;
  reports itself as `2026.7.0-latest`). Deviation #2 explains why this SHA and
  not the v2026.6.0 stable tag.
- **discourse-subscriptions**: **bundled in core** at that SHA
  (`plugins/discourse-subscriptions`, plugin version **2.8.1**) — deviation #1
- **launcher (`discourse_docker`)**: commit `472e9ce`
- **Mailpit**: `axllent/mailpit:v1.30.4@sha256:5a49a77c5bdbe7c5474450b4f46348d09949df3695257729c93a30369382d4f6`
- **Built image**: `local_discourse/noshit-f1-discourse` (3.37 GB = base + ~190 MB delta)

## Files

```
discourse.yml.template   launcher container config (rendered by setup.sh into the launcher tree)
mailpit.compose.yaml     the per-fixture SMTP sink (shared external network + loopback ports)
setup.sh                 LIGHT prep: dirs, network, .env, render yml, stage provision files
bootstrap.sh             ONE-TIME launcher build, df-gated with a live floor-safe watchdog
demo.sh                  REPEATABLE: start -> provision -> demo.py -> stop  (--keep / --reset)
demo.py                  the 6 proofs (mailsink.py for every sink claim)
provision/admin_seed.rb  non-interactive admin + API key + deterministic messaging/rate settings
provision/sidekiq_drain.rb   drains the sidekiq mail path to observable completion (absence anchor)
provision/clock_note.rb  F2 clock-story evidence (libc / sidekiq / scheduled-job enumerability)
.env.example .gitignore  non-secret template + ignore rules
```

Durable state lives OUTSIDE the repo under `/home/user/fixture-runtime/discourse/`:
`shared/standalone/` (postgres, uploads, logs — the DATA), `build-rw/` (the
build's shunted write paths — IMAGE-side state, see deviation #3),
`discourse_docker/` (third-party launcher).

## Run

```bash
./setup.sh          # light, idempotent (the others call it too)
./bootstrap.sh      # ONE-TIME df-gated build (measured: ~2.5 min at the baked-SHA pin)
./demo.sh           # REPEATABLE proof; stops the stack at the end (exit 0 == green)
./demo.sh --keep    # leave forum (8084) + sink (8031) running
./demo.sh --reset   # destroy container + wipe /shared DATA, re-init, then run
```

### Provisioning vs repeatable (honest split, measured)

- **One-time provisioning** = `./bootstrap.sh`: base pull (~4.5 min on this
  host's link; 3.18 GB on disk) + launcher build (**2 min 35 s** — the ember
  bundle is a build-cache hit at the baked SHA; only sprockets/theme targets
  compile). `demo.sh` auto-invokes it only if the built image is missing.
- **Repeatable demo** = `./demo.sh`: container/mailpit start + idempotent
  admin/API-key provision (`rails runner`, key rotated each run) + `demo.py`
  (the six proofs) + scoped stop. **Measured 78–83 s total, proof ~44 s; run
  twice green back-to-back** (TRANSCRIPT).

### "Down" for a launcher leg

`demo.sh` (no `--keep`) stops the Discourse container and removes the mailpit
container, **keeping the built image + durable state** so the next run is a fast
START (~40 s to healthy), not a rebuild. That is the appropriate "down" here.
Deep resets:

- `./demo.sh --reset` — wipes `/shared` (DB, uploads) only; **`build-rw/` is
  deliberately NOT wiped** (compiled assets are image-side state; wiping them
  would leave the committed image assetless — deviation #3). Next start
  re-inits an empty DB (~1–2 min).
- Full rebuild — `sg docker -c "docker rmi local_discourse/noshit-f1-discourse"`
  then `./bootstrap.sh` (which wipes and rebuilds `build-rw/` itself).

## SMTP plumbing (launcher container ↔ mailpit)

The launcher runs Discourse via `docker run` (not compose). host-gateway does
**not** work — mailpit is published on `127.0.0.1` only — so the leg uses a
shared user-defined bridge `noshit-f1-discourse-net` (created by `setup.sh`).
Mailpit joins it via compose (external network, service alias `mailpit`);
Discourse joins via the launcher yml's `docker_args: "--network ..."` (appended
verbatim to every `docker run` the launcher issues). Discourse sends to
`mailpit:1025` (unauthenticated, no TLS; mailpit accepts any/none). Proven live:
activation mail lands in the sink within ~0.5 s of signup.

## The six proofs (`demo.py`, all green — TRANSCRIPT has the run)

1. **Forum up + admin** — `/srv/status` 200 on 8084; admin-gated
   `/admin/plugins.json` 200 under the minted API key. Admin path: NOT the
   interactive rake — `provision/admin_seed.rb` via `rails runner` creates an
   **active** admin (`noshit_admin` / `admin@noshit.test`), grants admin, mints
   a global API key emitted on a marked stdout line that `demo.sh` captures
   into the gitignored `.env` (0600), never displayed.
   (`DISCOURSE_DEVELOPER_EMAILS` is also set — documents intent; the runner is
   what guarantees the state.)
2. **Signup E2 mail round-trip** — plain-HTTP `POST /u.json`; the endpoint
   required: **CSRF token** (`GET /session/csrf.json`, sent as `X-CSRF-Token`),
   **honeypot** (`GET /session/hp.json` → `password_confirmation=<value>`,
   `challenge=reverse(<challenge>)`), and a session cookie (one `requests`
   session throughout). Activation email arrives in the sink
   (`checkpoint → wait_new`; subject `Confirm your new account`); the hex token
   is parsed from the actual body and submitted as **`PUT
   /u/activate-account/<token>.json` — which re-checks the honeypot** (fields
   sent again). User verified **active=true** via `/admin/users/<id>.json`.
3. **Event-anchored absence** — `sidekiq_drain.rb` polls until
   `enqueued=0 busy=0` (Discourse sends all mail through sidekiq; that is the
   observable completed-delivery event, per FIXTURES §2.2 0.1.3 — never a bare
   timer), then `checkpoint → assert_none_new` per-address AND census-wide.
   Deferred-mail sources are disabled at provision and re-asserted in-run:
   `send_welcome_message=false`, `disable_digest_emails=true`. Note: sidekiq's
   *scheduled set* (future-dated periodic jobs) is nonzero and grows — that is
   mini_scheduler's forward calendar, not pending mail; the absence anchor is
   the immediate queue + busy workers.
4. **Bulk seed** — **55 topics in ~19–20 s** via `POST /posts.json` (admin API
   key + Api-Username), one deterministic pass, zero errors/stalls in the green
   runs, then API spot-checks. Content rate limits lifted via recorded
   `PUT /admin/site_settings/*` (`rate_limit_create_topic=0` etc.); the
   **admin-API request limiter** is a GlobalSetting raised via env
   (deviation #6).
5. **Subscriptions plugin, install-only** — listed in `/admin/plugins.json`
   (name `discourse-subscriptions`, version 2.8.1, `enabled=false` initially),
   enabled via its site setting, then the mounted-engine sweep: `/s/admin.json`
   → 200, `/s/admin` → 200, `/s/admin/subscriptions.json` → 200,
   `/s/admin/products.json` → 200, `/s/admin/plans.json` → 500 (a
   Stripe-unconfigured error — itself proof the route exists). 18
   `discourse_subscriptions_*` settings registered; the three key settings
   (`public_key`, `secret_key`, `webhook_secret`) confirmed **blank** — NO
   payment config, NO checkout attempt.
6. **Clock note (F2, evidence only)** — from inside the running container:
   Debian 12 bookworm, **glibc 2.36** → rung-2 `libfaketime` candidate;
   ruby 3.4.9; scheduled jobs run in the in-container **sidekiq 7.3.10** driven
   by **mini_scheduler**; **145 `Jobs::Scheduled` subclasses enumerable** (e.g.
   `Jobs::ActivationReminderEmails`) and each harness-triggerable via
   `Jobs.enqueue(Klass)` / `Klass.new.execute({})` through `rails runner`
   (rung 3 — the same shape the WooCommerce leg proved with wp-cron).

## Deviation record (every resistance met, in order encountered)

1. **`discourse-subscriptions` is BUNDLED in core, not an external clone.** The
   launcher's `BUNDLED_PLUGINS` lists it and rejects cloning it. It ships in
   `plugins/discourse-subscriptions` at the pinned core SHA (v2.8.1).
   Consequence: no separate plugin pin (the core pin IS the plugin pin), no
   second rebuild gate; "install-only + prove-it-loads" is satisfied by the
   bundled copy (enable setting + route sweep + blank keys).
2. **Core pinned to the base image's baked SHA, not the stable tag.** The base
   image bakes source + vendor/bundle (836 MB) + node_modules (786 MB) + an
   ember build cache at `bf386c2f...` (main, 2026-07-06). Pinning `version:` to
   that exact SHA makes checkout/bundle/pnpm near-no-ops and the ember build a
   cache hit — build delta ~190 MB in ~2.5 min instead of gigabytes in
   15–25 min. A 40-char SHA is as hard a pin as a tag; the tradeoff (recorded):
   it is a `main` commit a few days past `v2026.6.0`, reporting
   `2026.7.0-latest`.
3. **Shared-disk resistance and the `build-rw` shunt.** First build attempt
   (earlier the same day): watchdog abort mid-pull at 1.95 GiB free with a
   parallel leg building — reclaimed cleanly to 4.5 GiB. After the parallel leg
   banked, the base image alone unpacked to 3.18 GB leaving 2.6 GiB free —
   gates refused correctly; the coordinator then pruned banked-leg images
   (their prerogative — this leg never removes images it didn't create) to
   4.26 GiB. To fit, the two write-heavy build paths
   (`/var/www/discourse/tmp`, `public/assets`) are **bind-mounted out of the
   overlay** onto the durable disk: bind content bypasses the RW layer AND the
   `docker commit` duplicate, so those bytes land once, not twice. Consequence:
   the committed image does NOT contain compiled assets; the run-phase
   container serves them from the same mounts (one yml drives bootstrap and
   start, so they are always present). `build-rw/` is image-side state:
   `--reset` leaves it; `bootstrap.sh` wipes+rebuilds it. Result: minimum free
   observed during the whole build was **4.08 GiB** — the watchdog never fired
   and the 1.5 GiB floor was never approached.
4. **Ember bind-mounts FAILED and were removed (kept as a warning).** The first
   shunt attempt also bind-mounted ember `dist`/`tmp` under
   `app/assets/javascripts/` — but at this SHA the frontend has MOVED to
   `frontend/`, and Discourse's `.pnpmfile.cjs` treats an existing
   `app/assets/javascripts` dir as legacy cruft and runs `git clean -f -X` on
   it; docker's mkdir-for-bind had CREATED that path, and mount points are
   undeletable → pnpm (and the bootstrap) failed. Fix: drop those two binds;
   ember scratch is instead deleted at the end of pups (`run:` execs) — those
   bytes live in the build container's overlay upperdir, so deleting them
   genuinely frees disk before the commit copy.
5. **The launcher's static 5 GB preflight** refused to start at 4.26 GiB even
   though the shunted build peaks far lower. All launcher calls carry
   `--skip-prereqs`; the leg's LIVE df watchdog (floor 1.5 GiB, abort 2.2 GiB,
   8 s polls) supersedes the one-shot static check. The other skipped prereqs
   (docker version, RAM) are verified on this host.
6. **Admin-API request limiter (not a site setting).** With content rate limits
   lifted via API, the bulk seed still 429'd at topic 46 ("wait 30 seconds") —
   the global `max_admin_api_reqs_per_minute` (default 60/min), settable only
   by env. The yml sets `DISCOURSE_MAX_ADMIN_API_REQS_PER_MINUTE: 400` (bench
   host, loopback-only; applied by container recreate, not rebuild); `demo.py`
   also keeps a portable 429 handler that honors the server's `wait_seconds`
   and records any stalls (zero stalls in the green runs).
7. **Signup JSON omits `user_id` at this version** (live-response fix): the id
   is resolved via `/admin/users/list/all.json?filter=<email>&show_emails=true`
   right after signup; the activation proof then reads
   `/admin/users/<id>.json` as designed.
8. **Hostname/port.** Discourse refuses a bare IP; `DISCOURSE_HOSTNAME=localhost`
   (no `port` GlobalSetting exists at this SHA), so emailed links point at
   `http://localhost/...` (:80, unmapped). `demo.py` extracts the activation
   TOKEN and submits it against the mapped `:8084` — the token is what the
   server validates. The activation PUT must re-send the honeypot fields
   (verified in `users_controller#perform_account_activation`).
9. **`web.ratelimited.template.yml` omitted** so nginx abuse rate-limiting does
   not throttle the seed; the app-level limits are handled explicitly (above).

## What a re-verifier should do

```bash
cd platform/hosts/discourse && ./demo.sh   # expect exit 0 in ~1.5 min (image already built)
```
If the image is missing it bootstraps first (df-gated). During a `--keep` run:
forum `http://127.0.0.1:8084`, sink UI `http://127.0.0.1:8031`.

Apache-2.0 (see `../../LICENSE-CODE`).
