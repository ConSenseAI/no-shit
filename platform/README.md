# Fixture Platform

**Status: F0 proven (2026-07-10) · F1 staged build underway (2026-07-11).** The first running code in this repository — all four platform services demonstrated across three host legs, every demo deterministic from a cold start and independently re-run by the coordinator before commit. F1 (the E2 bulk phase, FIXTURES §9) now brings the remaining bench hosts up as staged legs.

| Leg | What it proved | Wall time |
|---|---|---|
| `hosts/killbill/` | Full trial→convert→charge→cancel on the engine test clock: $0 trial invoice at T0, $29.95 recurring invoice **charged** when the clock crossed T0+8d, cancel honored at the period boundary — 39 virtual days; plugin invoice/payment mail in the sink (`--with-email`) | ~96 s |
| `hosts/documenso/` | Real signup→verify→delete flow via the app's own endpoints; +31 virtual days in ~1 s (glibc libfaketime sidecar — Documenso itself is musl); post-deletion absence window held via `checkpoint → assert_none_new`; persona round-trip with a scripted +4h virtual delay | ~36 s |
| `hosts/ghost/` | Stripe sandbox test clock: frozen T0, advances landing exact `frozen_time`, forward-only invariant enforced, delete-cascade cleanup; Ghost member signup→magic-link→stored-member with mail in the sink (9/9); **full subscription lifecycle proven 9/9 once the key was re-scoped** — trialing → `trial_will_end` observed → $12.00 invoice paid at T0+8d1h → canceled at boundary, 39 virtual days in 31 s | ~28–45 s |

The Stripe subscription-lifecycle facts first ran as `BLOCKED: scope` (test-clock-only key), then **proved 9/9 the same day** after the operator re-scoped the key — `stripe-clockctl.py`'s capability-adaptive upgrade working as designed. Remaining F1 items on this leg: Ghost **billing coupling** (Stripe tiers inside Ghost member state — needs a webhook path, not just scopes) and production-parity MySQL. F0's empirical findings are folded into [`validation/FIXTURES.md`](../validation/FIXTURES.md) §2.1–§2.2 (0.1.1).

## F1 bench legs (staged)

F1 runs on this machine's disk budget in **staged rotation**: one host's image set at a time; images are volatile and re-pullable (pinned by digest), so they are pruned between hosts once a leg's artifacts are banked. Anything that must survive — seeded databases, captures — is bind-mounted under `/home/user/fixture-runtime/<leg>/` on the durable volume, never in docker named volumes (the docker store on this machine does not persist across reboots).

| Leg | What it proved | Wall time |
|---|---|---|
| `hosts/listmonk/` | Bulk seeding (200 subscribers in one ~1.2 s pass); campaign→sink full-list presence; unsubscribe round-trip over the app's own form (plain HTTP POST), state flip confirmed via the admin API; then the **presence+absence pair** — a second campaign delivered to every remaining subscriber with zero new mail to the unsubscribed address (`checkpoint("to:addr") → assert_none_new`) — the exact shape a clean unsubscribe-parity verdict certifies; double-opt-in confirm flow included. Finding: listmonk's sender is async and rate-limited, so **absence windows must anchor to the campaign-finished event, not a timer** (queued-but-unsent mail is a false-clean risk — feeds FIXTURES §7.1's residual-messaging window). | ~31 s |
| `hosts/woocommerce/` | Bulk seeding (132 published products across 3 categories in one ~16 s pass — single `wp eval-file`, idempotent); the full **plain-HTTP storefront E2**: shop → `?wc-ajax=add_to_cart` (session cookie asserted) → cart → scraped checkout nonce → `?wc-ajax=checkout` POST (guest, Cash-on-Delivery) → order recorded, status/total cross-checked via WP-CLI; customer **and** admin order mail in the sink, order number cross-checked mail↔store; census-wide and per-address absence window **anchored between completed wp-cron flushes**, not timers; rung-3 clock proven: `DISABLE_WP_CRON` + `wp cron event run --due-now` as the only job trigger (Action Scheduler rides the same path). Findings: current WooCommerce ships block checkout — the leg pins classic shortcode pages to keep the scriptable `wc-ajax` path; coming-soon mode must be disabled or the storefront is curtained; WooCommerce Subscriptions is paid and **not** installed — free wordpress.org stand-ins recorded in the leg README. | ~88 s cold / ~52 s warm |
| `hosts/twenty/` | The deliberate **co-location host** (nst+ndp+nli fixtures will live here) up cold in ~130 s (five services; first-boot migrations dominate); **batched seeding** — 120 companies + 120 people in one 0.64 s pass (~360 records/s) via the REST batch endpoints, verified by query-back; user-path entry over plain HTTP (workspace signup → token → authenticated reads); **invite-mail round-trip** captured in the sink with a host-reachable `SERVER_URL` link, plus the event-anchored absence pair (control address: 0 new; invitee: exactly 1, no residual); CSV export captured, row count == API total. Findings: Twenty v2.x env drift (`ENCRYPTION_KEY`, `EMAIL_DRIVER=SMTP`, `PG_DATABASE_URL`; PostgreSQL 16 required); auth mutations live on the `/metadata` GraphQL schema; single-tenant `signUp` is one-shot — later users arrive by invite; tokens must be re-minted after workspace activation; image is musl/Alpine, so F2 fake time takes the glibc-sidecar pattern aimed at the **worker** container. | ~130 s cold |
| `hosts/discourse/` | The canonical `discourse_docker` launcher tamed to the staged disk model: core pinned to the SHA already baked into the base image, and the build's write-heavy paths (`tmp/`, `public/assets`) shunted onto the durable disk via bind mounts — bypassing both the overlay layer and the `docker commit` duplicate → **~190 MB delta, 2-minute pups build** (vs. the stock 15–25 min/multi-GB). Proofs: signup over plain HTTP (scraped CSRF + honeypot fields — re-required at activation, source-verified) → activation mail in the sink at +0.5 s → token from the real body → `active=true` via admin API; per-address **and** census-wide absence anchored to **sidekiq drained to zero** (deferred mail disabled and recorded — the scheduled set is mini_scheduler's calendar, not pending mail); 55-topic one-pass API seed (~19–23 s; the env-only `max_admin_api_reqs_per_minute` raised and recorded, Retry-After handled); `discourse-subscriptions` **install-only** — now bundled in Discourse core (standalone repo archived 2025-07-14, still MIT), listed + enabled, admin routes mounted, every Stripe key setting blank. Clock story for F2: Debian glibc 2.36 → rung-2 libfaketime candidate; 145 enumerable `Jobs::Scheduled` classes, harness-triggerable (rung 3). | build ~3 min once; demo ~82 s |
**Serves:** [`validation/FIXTURES.md`](../validation/FIXTURES.md) §2 (the four amortized services) and §9 (F0 sequencing). The exit test, verbatim from there: *one fixture per host whose time script drives engine clock + app clock + sink jobs through a full trial-convert-cancel (resp. delete-confirm-window) cycle in minutes.*

F0 converts the build plan's tooling claims (Stripe/Kill Bill clocks, LD_PRELOAD fake time, SMTP sink capture) into working fact before the bulk fixture build. Code is Apache-2.0 (see [`LICENSE-CODE`](../LICENSE-CODE)).

## Layout

```
platform/
  harness/            shared helpers (host-agnostic)
    mailsink.py       Mailpit API client: capture checkpoints, presence waits, absence assertions
  hosts/
    killbill/         engine-native clock leg (FIXTURES §2.1 rung 1): trial → conversion → cancel via /1.0/kb/test/clock
    documenso/        stack-fake-time leg (rungs 2–3): deletion flow + sink absence window + persona stub
    ghost/            Stripe test-clock leg (rung 1): frozen-T0 advances + full subscription lifecycle 9/9
    listmonk/         F1 bench leg: bulk seeding, campaign→sink census, unsubscribe parity with per-address absence
    woocommerce/      F1 bench leg: storefront E2 (plain-HTTP checkout), bulk product seeding, rung-3 wp-cron clock
    twenty/           F1 bench leg: co-location host bring-up, batched CRM seeding, invite-mail round-trip + absence
    discourse/        F1 bench leg: launcher-built forum, signup→activation E2, sidekiq-drain-anchored absence, plugin install-only
```

Each host leg is a self-contained compose stack with its own Mailpit instance (per-fixture sink, per FIXTURES §2.2) and a deterministic `demo.sh` that brings the stack up, runs the proof, prints a virtual-time timeline, and tears down. Captured runs live in each leg's `TRANSCRIPT.md`.

## Port registry

Host-published ports are allocated here and nowhere else. Databases are **never** host-published (they stay on internal compose networks — the machine runs its own live Postgres on 5432).

| Leg | Service | Host port |
|---|---|---|
| killbill | Kill Bill API | 8080 |
| killbill | Mailpit UI / SMTP | 8025 / 1025 |
| documenso | app | 3600 |
| documenso | Mailpit UI / SMTP | 8026 / 1026 |
| ghost | app | 2368 |
| ghost | Mailpit UI / SMTP | 8027 / 1027 |
| listmonk | app | 9002 |
| listmonk | Mailpit UI / SMTP | 8029 / 1029 |
| woocommerce | app | 8083 |
| woocommerce | Mailpit UI / SMTP | 8028 / 1028 |
| twenty | app | 3001 |
| twenty | Mailpit UI / SMTP | 8030 / 1030 |
| discourse | app | 8084 |
| discourse | Mailpit UI / SMTP | 8031 / 1031 |

**Forbidden:** port **4000** (a live service unrelated to this project runs there — never bind, probe, or interfere with it), plus locally occupied `4040 4369 5100 5200 5432 8766`.

## Run conventions

- Docker group membership isn't in the login session's credentials on this machine; run everything as `sg docker -c "docker compose ..."`.
- Compose project names: `noshit-f0-<leg>` / `noshit-f1-<leg>` by phase — cleanup is always scoped (`docker compose -p <project> down`), never global.
- Secrets: none committed. Each leg ships `.env.example`; real `.env` files are generated locally and gitignored.

## What never lives here

- **Sealed-corpus fixtures.** The study's fixture implants, labels, and manifests are sealed until the report reveals them (PROTOCOL §4.2). This directory holds the *platform* and public demo fixtures that prove it — nothing whose label secrecy the study depends on.
- Credentials, API keys, payment-provider material of any kind.

## F0 exit criteria

1. **Engine-native clock** (killbill leg): a subscription with an 8-day trial created at T0 converts, invoices, and charges when the Kill Bill test clock — not wall time — passes T0+8d; cancellation honored at period boundary. Evidence: transcript with the virtual-time timeline.
2. **App/sink coupling** (documenso leg): an account-deletion flow emits its confirmation into the leg's Mailpit sink; a post-deletion absence window ("no further mail matching M since checkpoint") holds as a first-class assertion via `harness/mailsink.py`.
3. **Stack-level fake time** (documenso leg): app-side scheduled behavior driven past a multi-day boundary in minutes via LD_PRELOAD fake time — or, where the host resists it, the documented fallback (harness-triggered jobs, FIXTURES §2.1 rung 3), with the resistance recorded.
4. **Persona stub** (documenso leg): a scripted support persona observes a trigger message and replies after a *scripted virtual delay* (not wall time), round-trip visible in the sink.

Deviations from FIXTURES §2 assumptions discovered during F0 are recorded in each leg's README and fed back into `validation/FIXTURES.md` at its next bump.
