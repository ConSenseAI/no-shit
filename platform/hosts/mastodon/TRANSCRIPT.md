# TRANSCRIPT — noshit-f1-mastodon (real runs, 2026-07-11)

Host: `/dev/mapper/dmroot` 20 GB shared root. Docker via `sg docker -c`. All host
ports loopback-only. Mastodon **v4.6.2** (web + sidekiq; **NO streaming — the
streaming service's default port is 4000, a forbidden live-service port**).

## Summary

| Proof | Status | Evidence (below) |
|---|---|---|
| 1. Signup → confirmation-mail → confirmed | **GREEN** | mail in sink at +0.6 s; emailed token followed; `confirmed=true` via admin API |
| 2. nli★ CSV export | **GREEN** | `following.csv` 2 data rows == seeded `following_count` 2; 5 CSVs banked |
| 3. nli★ FULL ARCHIVE (headline) | **GREEN** | request → sidekiq drain → "archive ready" mail → ZIP download; `outbox.totalItems=6==6`, `actor @f1arch…` |
| 4. nli DELETION + ABSENCE | **GREEN** | live baseline=1 → deleted → gone (admin absent + public 404) → per-address + census `assert_none_new`, sidekiq-anchored |
| 5. Clock note (F2 evidence) | captured | Debian 13 trixie, glibc 2.41, ruby 4.0.5, sidekiq 8.1.6, 18 Scheduler workers |
| Repeatable demo | **exit 0 cold & warm** | cold `--reset`: proof 78 s / total 174 s; warm: proof ~69 s / total ~158 s |

Cold `./demo.sh --reset` (fresh DB) and warm `./demo.sh` (seeded DB reused) both
exit 0 with all five proofs green. Per-run accounts carry a timestamp suffix, so
warm re-runs never collide (and the 7-day archive cooldown never blocks).

## df gate readings (rule: floor 1.5 GiB — never approached)

| Gate / event | Root free | Action |
|---|---|---|
| Session start (pre-pull) | **7.8 GiB** | df gate before any pull |
| Before redis / postgres pulls | 8.0 GiB | pulled (small: 39 MB / 292 MB) |
| Before Mastodon pull (~334 MB dl) | **8.0 GiB** | gate PASS → pulled |
| After all 3 pulls (~1.1 GB on disk) | **6.6 GiB** | steady |
| `demo.sh` df at start | 6.6 GiB | — |
| **df gate before db setup** | **~7 GiB** (df -BG rounds) | PASS (floor 1.5) |
| After each demo run / df at end | **6.6 GiB** | steady |
| Minimum observed all session | **6.6 GiB** | floor 1.5 GiB never approached |

New pulls: `ghcr.io/mastodon/mastodon:v4.6.2` **766 MB**, `postgres:15-alpine`
292 MB, `redis:7-alpine` 39 MB = **~1.1 GB** (budget 2.2 GB). `axllent/mailpit:
v1.30.4` reused (34 MB). The separate `mastodon-streaming` image was **not
pulled**.

## Cold-start run (`./demo.sh --reset`) — verbatim highlights

```text
[demo] df gate before db setup: 7 GiB free (floor 1.5)
[demo] up infra (db, redis, mailpit) --wait ...   (all Healthy)
[demo] fresh DB -> rails db:schema:load db:seed ...
[demo] up app (web, sidekiq) --wait ...           (web + sidekiq Healthy)
[demo] provision: open registration ...
[demo]   owner created (password captured into .env, redacted)
[demo]   admin token minted into ./.env (0600) [redacted]

[seed] seed accounts ready: ['f1seed_a', 'f1seed_b', 'f1seed_c'] (created=3, existing=0)
[seed] follow graph: f1seed_a->f1seed_b,f1seed_c, f1seed_b->f1seed_c, f1seed_c->f1seed_a (new edges: 4)
[seed] statuses: posted=102 in 6.36s (16/s), total now 102 across 3 accounts
[seed]   @f1seed_a: statuses=34 following=2 followers=1
[seed]   @f1seed_b: statuses=34 following=1 followers=1
[seed]   @f1seed_c: statuses=34 following=1 followers=2
```

### Proof timeline (cold run)

```
    WALL  EVENT
    0.3s  Mastodon 4.6.2 up on 127.0.0.1:3002 (web+sidekiq; NO streaming); admin @noshit_owner
    5.3s  signup POST accepted over plain HTTP (CSRF + honeypots + agreement + 3s gate); @f1signup1783751072
    5.9s  mail round-trip CLOSED: f1-signup-1783751072@localhost signed up -> emailed -> confirmed -> confirmed=true
    6.7s  CSV export: following.csv 2 rows == following_count 2; 5 export files captured to captures/
   28.x   archive requested for @f1arch1783751072 (6 statuses); awaiting BackupWorker via sidekiq
   39.1s  ARCHIVE headline CLOSED: request->drain->mail->download; ZIP outbox.totalItems=6 == 6, actor @f1arch1783751072
   60.1s  msg channel was LIVE to f1del1783751072@localhost while active (baseline=1 transactional mail)
   60.x   @f1del1783751072 self-deleted over plain HTTP (settings delete + password confirmation)
   70.3s  DELETION absence pair held: was live (baseline 1) then SILENT after deletion (per-address + census, sidekiq-anchored)
   78.1s  clock note captured
[  78.1s] ALL ASSERTIONS PASSED in 78.1s (sink holds 9 message(s))
[demo] demo.py exit code: 0
```

## Proof 1 — signup mail round-trip (what the form took)

```
form requirements: authenticity_token (CSRF) + honeypots user[confirm_password]/user[website]
  left BLANK + user[agreement]=1; email domain must resolve (MX/A — @localhost does);
  and a >3s dwell (REGISTRATION_FORM_MIN_TIME anti-bot gate) — sleeping 4.0s
POST /auth accepted -> 302 -> https://localhost:3002/auth/setup (account created, pending confirm)
confirmation mail in sink: subject='Mastodon: Confirmation instructions for localhost' to=f1-signup-…@localhost
emailed link host: https://localhost  (rewritten to http://localhost:3002 to follow — token is what the server validates)
followed emailed confirmation link -> 302 -> https://localhost:3002/web/start
admin API confirms @f1signup… confirmed=True approved=True
```
Requirements met: `X-Forwarded-Proto: https` (force_ssl), Secure cookie sent over
http, scraped CSRF, **≥3 s dwell**, `@localhost` email (fake domains fail MX),
honeypots blank. See README deviations #1–#7.

## Proof 2 — CSV export (files banked to captures/)

```
seeded @f1seed_a following_count (public API) = 2
follows.csv    -> 200, 3 lines (2 data rows)   saved f1seed_a-follows.csv   (120 bytes)
blocks.csv     -> 200, 0 lines (0 data rows)   saved f1seed_a-blocks.csv
mutes.csv      -> 200, 1 lines (0 data rows)   saved f1seed_a-mutes.csv     (header only)
lists.csv      -> 200, 0 lines (0 data rows)   saved f1seed_a-lists.csv
bookmarks.csv  -> 200, 0 lines (0 data rows)   saved f1seed_a-bookmarks.csv
PASS following.csv data rows (2) == seeded following_count (2)
```

## Proof 3 — FULL ARCHIVE (the headline), request → drain → mail → ZIP

```
per-run fresh archive account @f1arch1783751072 (id=…); posted 6 statuses
POST /settings/export (request archive) -> 302
sidekiq | enqueued=0 busy=0 scheduled=… processed=… failed=0     (BackupService ran)
'archive ready' mail in sink: 'Your archive is ready for download' to f1arch…@localhost
downloaded archive -> 200, 3518 bytes, ZIP magic present   (GET /backups/<id>/download -> /system/backups/…zip)
archive members: ['outbox.json', 'likes.json', 'bookmarks.json', 'actor.json']
outbox.json totalItems (6) == posted statuses (6)
actor.json  preferredUsername == @f1arch1783751072 (type=Person)
saved captures/f1arch1783751072-archive.zip
```
The archive is a **ZIP** (not tar.gz), containing the ActivityPub actor + outbox.
Archives are rate-limited to **once per 7 days per account** → a fresh account per
run keeps re-runs green (README deviation #9; F2 virtual-clock target).

## Proof 4 — DELETION + ABSENCE (the certification-shaped deliverable)

```
per-run delete account @f1del1783751072; baseline mail to its address = 1
PASS  msg channel was LIVE to f1del…@localhost while active (baseline=1 transactional mail)
POST /settings/delete (password-confirmed) -> 302 -> /auth/sign_in (deletion accepted, session ended)
sidekiq | enqueued=0 busy=0 …     (deletion/purge worker ran)
PASS  account gone/suspended per admin API (present=False)
PASS  public GET /api/v1/accounts/<id> -> 404 (gone)
PASS  ABSENCE holds per-address: 0 further mail to f1del…@localhost after deletion (baseline stays 1)
PASS  ABSENCE holds census-wide: no unexpected mail since the deletion drain
```
The absence pair — a **live baseline** (the account received transactional mail
while active) then **silence** after deletion — is asserted per-address **and**
census-wide, both anchored to a **sidekiq drain** (`enqueued=0 busy=0`), never a
timer. This is the clean-deletion shape an nli verdict certifies (ATTAINABILITY
O-2).

## Proof 5 — clock-story note for F2 (verbatim)

```
os_release=Debian GNU/Linux 13 (trixie)
ruby=4.0.5 platform=x86_64-linux
libc=ldd (Debian GLIBC 2.41-12+deb13u3) 2.41
sidekiq=8.1.6 (all mail/backup/deletion jobs run here)
scheduler_worker_classes=18
sample_scheduler=["Scheduler::AccountsStatusesCleanupScheduler", "Scheduler::AutoCloseRegistrationsScheduler",
  "Scheduler::CollectionItemCleanupScheduler", "Scheduler::Fasp::FollowRecommendationCleanupScheduler",
  "Scheduler::FollowRecommendationsScheduler", "Scheduler::IndexingScheduler"]
enumerable_and_triggerable=true (Scheduler::* workers; run via Klass.new.perform / perform_async)
nli_window archive_cooldown=7d (Backup: one request per account per 7 days)
nli_window archive_link=served from public/system while the Backup row lives
nli_window deletion=self-serve delete suspends immediately, purge job async
```
Rung-2 candidate: **glibc 2.41 / Debian → `libfaketime` LD_PRELOAD viable** (no
musl sidecar, unlike the Alpine legs). Rung-3: the 18 `Scheduler::*` jobs are
ordinary classes, enumerable and individually harness-triggerable via
`rails runner`.

## What the sink held (the msg-channel census for one cold run)

At exit the sink held **9 messages**: 3 seed-account "Password changed" provisioning
notices (baseline), the signup **confirmation** mail, the archive account's
"Password changed" + **"archive ready"** mails, and the delete account's baseline
"Password changed" — and **zero** further mail to the deleted address after its
deletion (the absence). Every claim was made through `harness/mailsink.py`.

## End state

- Repeatable demo verified green **cold (`--reset`) and warm** (exit 0).
- Stack **DOWN** (scoped `docker compose -p noshit-f1-mastodon down`; no
  containers remain; **nothing ever bound host port 4000**).
- Durable state under `/home/user/fixture-runtime/mastodon/`: `db/` (54 MB
  Postgres), `redis/`, `system/` (media + archives), `captures/` (archive ZIPs +
  CSVs).
- Root free at close: **6.6 GiB** (floor 1.5 never approached). Nothing committed.
