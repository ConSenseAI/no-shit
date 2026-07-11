# noshit-f1-mastodon — F1 bench leg (Mastodon, the **nli★ gold standard**)

Proves the fixture platform's **export / migration / delete baseline** on a new
heavy host: production-parity **Mastodon** (v4.6.2) brought up by compose, driven
through its own REST API + settings web flows and its Mailpit sink. Mastodon is
the bench's **`no-lock-in` (nli) gold-standard host** (FIXTURES §3): its account
**archive** (ActivityPub actor+outbox), **CSV data exports**, and **clean
self-deletion** are the *reference clean flows* that later `nli` degradation
implants are measured against. This leg is PUBLIC platform code (Apache-2.0):
**no study fixtures, no labels, no implants.**

> **Status (2026-07-11): COMPLETE — repeatable proof GREEN cold and warm.**
> `./demo.sh --reset` (cold, fresh DB) and `./demo.sh` (warm, seeded DB reused)
> both exit 0 with all five proofs green (~78 s proof, ~174 s incl. cold
> up/schema/seed/teardown). Every resistance met is in the Deviation record.
> Evidence: [`TRANSCRIPT.md`](./TRANSCRIPT.md).

## What this leg proves

| Platform service (FIXTURES §2) | Proven here | How |
|---|---|---|
| **§2.2 — messaging capture + absence** (O-2, the `msg` channel) | ✓ | Confirmation mail and "archive ready" mail captured in this leg's Mailpit; the **clean-deletion absence pair** (a live baseline mail, then `checkpoint → assert_none_new` per-address **and** census-wide) anchored to a **sidekiq drain** (`enqueued=0 busy=0`), never a timer. `MP_MAX_MESSAGES=0` keeps retention unbounded while the window is open. |
| **§2.3 — state seeding / bulk content** (O-8) | ✓ | REST-API seed: **3 accounts + a follow graph + 102 statuses in one ~6 s pass** (≈16/s), verified by query-back. |
| **§3 — nli★ gold-standard clean flows** | ✓ | **CSV export** (following.csv rows == seeded following_count), **full account archive** (request → drain → mail → download the ZIP → verify the ActivityPub `outbox.totalItems` == posted count + `actor.preferredUsername`), and **clean self-deletion** (gone via admin API + public 404, then silence). These are the *baselines the implants degrade.* |

### The nli★ role (why the headline is export + delete)

`no-lock-in` degradation fixtures are built by taking one of these clean flows and
**breaking it in a measurable way** — a truncated/again-rate-limited archive, an
export that drops rows, a deletion that leaves the account reachable or keeps
mailing it. This leg establishes the **clean pole** for each, end to end with sink
evidence, so an implant's deviation is diffable against a known-good baseline.

## Ports (loopback only; registry-allocated)

| Service | Host bind | Notes |
|---|---|---|
| Mastodon **web** (puma) | `127.0.0.1:3002` → container `:3000` | REST API + web UI (the app under test) |
| Mailpit UI + REST API | `127.0.0.1:8032` → `:8025` | `harness/mailsink.py` talks here |
| Mailpit SMTP | `127.0.0.1:1032` → `:1025` | Mastodon sends here internally |
| Postgres, Redis | **none** | internal network only — **never** host-published |

### 🛑 Streaming service OMITTED — the port-4000 hazard

Mastodon's **streaming** service listens on **port 4000** by default, and host
port 4000 on this machine runs a **critical unrelated live service**. **This leg
runs NO streaming container at all.** It is not needed for any proof here: the
`web` (puma) container serves the full REST API and the web UI (which simply polls
instead of receiving live pushes when streaming is absent), and every proof rides
the REST API + session web endpoints. The Mastodon web image exposes only
`3000/tcp`; nothing in `compose.yaml` publishes, exposes, or references host port
4000. (Verified: `grep 4000 compose.yaml` matches only hazard-documenting
comments.)

## Image pins & sizes (all digest-pinned in `compose.yaml`, verified 2026-07-11)

| Image | On-disk | New pull? | Digest |
|---|---|---|---|
| `ghcr.io/mastodon/mastodon:v4.6.2` | **766 MB** | **yes** | `sha256:c5a92a6ec505086060a5a1fdec3be286da7f3cbd06e5158359e7f720e14b912c` |
| `postgres:15-alpine` | 292 MB | yes | `sha256:3d0f7584ed7d04e27fa050d6683a74746608faf21f202be78460d679cc56461f` |
| `redis:7-alpine` | 39 MB | yes | `sha256:6ab0b6e7381779332f97b8ca76193e45b0756f38d4c0dcda72dbb3c32061ab99` |
| `axllent/mailpit:v1.30.4` | 34 MB | **no (reused)** | `sha256:5a49a77c5bdbe7c5474450b4f46348d09949df3695257729c93a30369382d4f6` |

New disk footprint: **~1.1 GB** (766 + 292 + 39), well under the leg's 2.2 GB
budget. The separate `mastodon-streaming` image is **deliberately not pulled**.
Root free stayed at **6.6 GiB** throughout (floor 1.5 GiB never approached).

## Run

```bash
cd platform/hosts/mastodon
./demo.sh            # staged up -> provision -> seed -> 5 proofs -> down (exit 0 == green)
./demo.sh --keep     # leave web (:3002) + sink (:8032) running
./demo.sh --reset    # wipe durable DB/redis/media first (cold start), then run
```

Prereqs: Docker via the `sg docker` wrapper, `python3` + `requests`, `openssl`.

`setup.sh` generates the gitignored `.env` (0600) using **the Mastodon image's own
tasks** — `rails secret` ×2 (SECRET_KEY_BASE, OTP_SECRET),
`rake mastodon:webpush:generate_vapid_key` (VAPID pair),
`rake db:encryption:init` (the v4.3+ ActiveRecord encryption trio) — plus a random
POSTGRES_PASSWORD and MASTO_SEED_PASSWORD. No secret is ever printed. Only
`.env.example` is committed.

### Provisioning vs demo (honest split)

- **Provisioning** (`demo.sh`, before the proof; idempotent): staged bring-up
  (infra → **schema** → app, because Mastodon `/health` needs a migrated DB),
  `Setting.registrations_mode = open`, the **Owner admin** (`tootctl accounts
  create … --role Owner`), and a minted **OAuth admin token** (`rails runner`
  Doorkeeper) captured into `.env` (0600, redacted). Schema is `db:schema:load
  db:seed` on a fresh DB, `db:migrate` on a warm one.
- **Demo** (`seed.py` + `demo.py`): the bulk seed + the five proofs. Must re-run
  green — per-run accounts use a timestamp suffix, so warm re-runs never collide.

### The five proofs (`demo.py`; every sink claim via `harness/mailsink.py`)

1. **SIGNUP E2 mail round-trip** — register a NEW per-run account over plain HTTP
   at the real `/auth` flow → confirmation mail in the sink → follow the emailed
   token → `confirmed=true` via the admin API. (What the form took: see
   deviations #3–#7.)
2. **nli★ CSV export** — web-login a seeded account → download
   `/settings/exports/{follows,blocks,mutes,lists,bookmarks}.csv` → assert
   `following.csv` data rows == the account's seeded `following_count`; all saved
   to `captures/`.
3. **nli★ FULL ARCHIVE (headline)** — a per-run fresh account posts statuses →
   `POST /settings/export` (request archive) → **sidekiq drain** → "Your archive
   is ready for download" mail → download the **ZIP** from `/backups/:id/download`
   → verify `outbox.json` `totalItems` == posted count and `actor.json`
   `preferredUsername`. Saved to `captures/`.
4. **nli DELETION + ABSENCE** — a per-run fresh account receives a live baseline
   mail, then self-deletes over plain HTTP (`DELETE /settings/delete` with
   password confirmation) → account **gone** (admin API absent + public 404) →
   **sidekiq drain** → per-address **and** census-wide `assert_none_new`. The
   clean-deletion evidence the criterion certifies.
5. **CLOCK-STORY NOTE for F2** (evidence only) — libc / sidekiq / scheduled-job
   enumerability + the nli windows this host carries natively.

### Durability & reset

Durable state is bind-mounted under `/home/user/fixture-runtime/mastodon/`:
`db/` (Postgres), `redis/`, `system/` (media **and account archives**), `captures/`
(the CSV + archive artifacts each run banks). It survives `down`. Postgres and
Redis run as the host uid (1000) so `db/`/`redis/` reset without sudo; `system/`
is owned by the image uid **991** (see deviation #8), so `--reset` wipes it
**container-assisted** (a one-shot `docker run --user 0 … rm`), then `setup.sh`
recreates + re-chowns it. `--reset` cost: a fresh `db:schema:load db:seed`
(~11 s) + reseed (~40 s).

## Clock story for F2 (from `provision/clock_note.rb`, run in the sidekiq container)

- **Debian GNU/Linux 13 (trixie), glibc 2.41** → **rung-2 `libfaketime`
  LD_PRELOAD candidate** (glibc, not musl — no sidecar needed, unlike the
  Alpine/musl legs).
- Ruby 4.0.5; **all mail / backup / deletion jobs run in sidekiq 8.1.6**.
- **18 `Scheduler::*` recurring worker classes** enumerable (e.g.
  `Scheduler::AccountsStatusesCleanupScheduler`), each **harness-triggerable** via
  `Klass.new.perform` / `Klass.perform_async` through `rails runner` — the rung-3
  hook (same shape the WooCommerce/Discourse legs proved).
- **nli windows this host carries natively** (F2 virtual-clock targets):
  - **archive cooldown = 7 days** per account (`Backup` allows one request per
    account per 7 days). This leg sidesteps it with a **per-run fresh archive
    account**; F2 must drive this cooldown on a virtual clock to re-request
    without a fresh account.
  - **deletion** is suspend-immediately + async purge (a grace/purge window a
    degradation fixture could stretch).
  - archive-link availability is bounded by the `Backup` row's lifetime.

## Deviation record (every resistance met, in order of discovery)

Feeds back into `validation/FIXTURES.md` §2. The load-bearing ones for the bulk
build are **#1/#2** (running production Mastodon over a loopback http port) and
**#9** (the archive cooldown as an F2 clock target).

1. **Production `force_ssl` — plain http 301-redirects to https.** Mastodon
   production redirects `http://…/` → `https://…/`. Fix (the standard TLS-proxy
   model, not a Mastodon hack): every demo/seed client sends
   **`X-Forwarded-Proto: https`**, so the app treats the request as
   TLS-terminated and serves normally over the plaintext loopback port. `/health`
   is exempt (200 plain) — the compose healthcheck uses it.
2. **Secure cookies + emitted https links (the LOCAL_DOMAIN combination).** With
   `X-Forwarded-Proto: https`, Mastodon marks the session cookie **Secure**, so
   `requests` won't send it back over http → CSRF/session breaks (HTTP 422). Fix:
   the clients mark cookies non-secure (`return_ok_secure`/`c.secure=False`) so
   the loopback http port still gets them. Generated links (emails) use
   `LOCAL_DOMAIN=localhost` → `https://localhost/…`; the clients rewrite
   `https://localhost[:port]` → `http://localhost:3002` to follow them (the
   token/path is what the server validates). **The exact env combination:**
   `RAILS_ENV=production`, `LOCAL_DOMAIN=localhost`, **no `WEB_DOMAIN`**,
   `RAILS_SERVE_STATIC_FILES=true` — plus the client-side `X-Forwarded-Proto` +
   cookie-desecure + link-rewrite. There is no supported "emit http links" toggle
   in Mastodon since v3.0; this is the least-hacky loopback approach.
3. **Registration is CLOSED by default.** A fresh instance has
   `registrations_mode=none`; `GET /auth/sign_up` 302s away. Provisioning sets
   `Setting.registrations_mode = 'open'` (auto-approve, no rules) before any
   signup.
4. **Anti-bot form-timing gate.** `RegistrationFormTimeValidator`
   (`REGISTRATION_FORM_MIN_TIME = 3.seconds`) silently rejects a signup POST that
   arrives < 3 s after the form render (a `:base` "too_fast" error, 200 re-render,
   **no account, no visible field error**). The client **waits 4 s** between the
   `GET /auth/sign_up` and the `POST /auth`.
5. **Email domain must resolve (MX/A).** Mastodon's email validator rejects
   addresses whose domain has no MX/A record ("does not seem to exist") — so
   `@noshit.test`/`@example.com` fail. `@localhost` resolves (127.0.0.1) and
   passes; all fixture addresses use `@localhost`. (Mail still lands in Mailpit
   regardless of the address domain.)
6. **Honeypots.** The signup form carries `user[confirm_password]` and
   `user[website]` honeypots that must be submitted **blank**; the real fields are
   `user[password]`/`user[password_confirmation]` + `user[account_attributes]
   [username]` + `user[agreement]=1` + the scraped `authenticity_token`.
7. **`tootctl --confirmed` ≠ approved.** A tootctl-created account confirms email
   but is left **`approved=false`** if the instance was ever in approval mode →
   its OAuth tokens are rejected ("login pending approval"). Provisioning opens
   registration **first** (auto-approve) and the token/prepare runners set
   `approved: true` defensively.
8. **Image uid 991 + `/opt/mastodon` is mode 700.** web/sidekiq **must** run as
   the image's own uid 991 (can't run as another uid — the app dir is
   owner-only), so the `public/system` bind-mount is chowned to 991 by `setup.sh`
   (via the image itself as root) and `--reset` wipes it container-assisted.
   Postgres/Redis run as uid 1000 for sudo-less reset.
9. **The account archive is rate-limited to once per 7 days per account** — and
   is a **ZIP, not a tar.gz** (deviation #10). Each run uses a **fresh archive
   account** so the cooldown never blocks a re-run; **recorded as an F2
   virtual-clock target** (drive the 7-day `Backup` cooldown on a virtual clock).
10. **Archive format is `.zip`** (members `outbox.json`, `actor.json`,
    `likes.json`, `bookmarks.json`) — not the tar.gz the plan assumed. Verified
    via `zipfile`: `outbox.json` is an `OrderedCollection` whose `totalItems`
    equals the posted status count; `actor.json` is a `Person` with the expected
    `preferredUsername`.
11. **Deletion is async (suspend-then-purge).** `DELETE /settings/delete`
    suspends immediately and enqueues the purge worker; the public API still 200s
    until the purge runs. The proof **drains sidekiq first**, then asserts gone
    (admin absent + public 404) — matching the real completed-deletion event.
12. **Admin-API account entity nests public counts under `.account`.** `GET
    /api/v1/admin/accounts` returns admin entities without a top-level
    `following_count`; the proof reads it from the public
    `/api/v1/accounts/lookup?acct=…` instead.
13. **Headless secret generation.** `rake secret` was removed in Rails 8 —
    Mastodon 4.6 uses **`rails secret`**. The generation one-shots boot with
    `SECRET_KEY_BASE_DUMMY=1` so the tasks run before a real secret exists.
14. **Schema fresh-vs-warm + `ProtectedEnvironmentError`.** `db:schema:load` is
    refused against a **populated** production DB; the demo detects fresh
    (`SELECT to_regclass('public.accounts')` is null → `schema:load db:seed`) vs
    warm (→ `db:migrate`). The detection SQL has spaces, so it must be passed as
    one properly-quoted arg through `sg docker -c` (a `$*`-splitting helper
    silently mangles it — the bug that first made a warm DB look "fresh").
15. **Provisioning "Password changed" mail is a *feature*.** Setting the
    per-run accounts' known password emits a transactional security email. For the
    deletion proof this is the **live baseline** (`baseline≥1`, asserted) that the
    clean deletion then silences — exactly the "channel was live, then silent"
    shape a clean-deletion verdict needs. It is drained/settled *before* each
    absence checkpoint, so the windows stay sound.

## What a re-verifier should do

```bash
cd platform/hosts/mastodon && ./demo.sh --reset   # cold; expect exit 0 in ~3 min
# or, against the seeded DB from a prior run:
./demo.sh                                          # warm; expect exit 0 in ~2.5 min
```
During a `--keep` run: web `http://localhost:3002`, sink UI `http://127.0.0.1:8032`.
Artifacts land in `/home/user/fixture-runtime/mastodon/captures/` (the archive
ZIP + the CSVs). Apache-2.0 (see `../../LICENSE-CODE`).
