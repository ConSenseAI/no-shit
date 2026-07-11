# noshit-f1-woocommerce

F1 platform-proof, **WooCommerce leg** (the E2-bulk bench shape). A
self-contained compose stack that proves the platform's **seeding**,
**payment-spine**, and **messaging-capture** services on a new host, with a
deterministic `demo.sh` that cold-starts, installs, seeds, runs the proof, and
tears down in ~90 s. This is PUBLIC platform code (Apache-2.0) — no study
fixtures, no labels, no implants.

| Claim served | Proven here | How |
|---|---|---|
| **FIXTURES §2.3 — state seeding, bulk content** ("hundreds-per-collection") | ✓ | one command seeds **132 published products across 3 categories in 16.0 s** (single `wp eval-file` pass, deterministic SKUs/prices, idempotent re-run: `created=0 skipped=132` in 2.4 s) |
| **FIXTURES §2.3 — payment spine** (names "WooCommerce's test gateway") | ✓ | built-in **offline Cash-on-delivery gateway**: a real guest checkout settles to `processing` with an order record and receipt mail — no external processor, no keys |
| **FIXTURES §2.2 — msg-channel census + absence** | ✓ | order mail (customer + admin) captured in the leg's Mailpit; census listed in full; **absence window held via `checkpoint → assert_none_new`, anchored between completed events** (see below) |
| **FIXTURES §2.1 rung 3 — harness-triggered jobs** | ✓ | `DISABLE_WP_CRON=true` (fixture-grade); due jobs fire **only** under `wp cron event run --due-now`, captured in the transcript |
| **F1 / E2 phase** (FIXTURES §9: "E2 bulk — stateful single-sitting flows across the bench") | ✓ | the checkout is an E2-tier flow: stateful (session cart → order), single sitting, real time, driven end-to-end from the user's entry point |

## Run it

Prerequisites: Docker + Compose, `openssl`, `python3` (with `requests`), and
the `sg docker` wrapper this machine uses. Then:

```bash
cd platform/hosts/woocommerce
./demo.sh            # up --wait -> install -> seed -> proof -> down (durable data survives)
./demo.sh --keep     # same, but leave the stack running (store :8083, sink UI :8028)
./demo.sh --reset    # wipe the durable runtime first, then run from scratch
```

Exit 0 = all proofs green. A captured pristine cold run is in
[`TRANSCRIPT.md`](./TRANSCRIPT.md) (total 90 s; proof phase 25.5 s).

**Durable state & the reset path.** All state lives in bind mounts under
`/home/user/fixture-runtime/woocommerce/` (`db/`, `html/`) — durable disk, not
named volumes (the docker store here is volatile). Teardown (`down`) never
touches it. The mariadb/wordpress entrypoints chown those trees to in-container
uids, so a plain `rm -rf /home/user/fixture-runtime/woocommerce/*` from the
login user hits permission errors — the working reset is the container-assisted
wipe wired into `./demo.sh --reset` (an `alpine` run scoped to that one bind
mount), after which the leg re-bootstraps from nothing. `.env` survives resets;
regenerate with `./setup.sh --force`.

## Stack

Compose project **`noshit-f1-woocommerce`**. Host ports are loopback-bound
(`127.0.0.1`) and limited to this leg's registry allocation (app **8083**,
Mailpit UI **8028** / SMTP **1028** — registry row to be added to
`platform/README.md` at fold-in). Cleanup is always scoped
(`sg docker -c "docker compose -p noshit-f1-woocommerce down"`), never global.

| Service | Image (pinned by digest) | Host port | Notes |
|---|---|---|---|
| `wordpress` | `wordpress:latest@sha256:e36cd332…` = WordPress **7.0.1**, PHP 8.3.32-apache | `8083` | the real app; WooCommerce **10.9.4** installed from wordpress.org |
| `db` | `mariadb:lts@sha256:628f228f…` | **none** | internal network only — never host-published |
| `mailpit` | `axllent/mailpit:v1.30.4` | `8028` UI/API, `1028` SMTP | per-fixture sink; `MP_MAX_MESSAGES=0` (no auto-prune while absence windows are open) |
| `wpcli` | `wordpress:cli@sha256:f8aeb681…` = WP-CLI 2.12.0 | **none** | tools container (`profiles: [tools]`), invoked per-command via `compose run --rm`; runs as uid 33 |

Secrets: none committed. `setup.sh` generates `.env` (gitignored; hex-only
values) with the DB passwords and admin credentials; `.env.example` carries
placeholders. No script echoes `.env` contents; the admin password expands
only inside the wpcli container's shell.

### Image sizes (pull budget)

| Image | Size | Pulled |
|---|---|---|
| `wordpress:latest` (7.0.1) | 762 MB | new |
| `mariadb:lts` | 341 MB | new |
| `wordpress:cli` (2.12.0) | 207 MB | new |
| `axllent/mailpit:v1.30.4` | 34 MB | already local — reused |

New pulls total **≈1.31 GB** (budget ≤1.6 GB). `mariadb:lts` chosen over
`mysql:8` (~600 MB) per budget guidance.

## Mail wiring (no third-party SMTP plugin)

[`mu-plugins/mailpit-smtp.php`](./mu-plugins/mailpit-smtp.php) — a 25-line
must-use plugin bind-mounted read-only into `wp-content/mu-plugins/` — hooks
`phpmailer_init` and points PHPMailer at `mailpit:1025` (plain SMTP, internal
network). Because it's an mu-plugin it is active from the first request and
cannot be deactivated from wp-admin; because the same env is set on the wpcli
container, **CLI-originated mail routes to the sink too** (the transcript's
`Payment gateway "Cash on delivery" enabled` admin notice was sent by the
wpcli container during store configuration — the census covers every
`wp_mail()` source in the stack).

## The real flow driven (E2 proof, `demo.py`)

Plain HTTP against `127.0.0.1:8083` with `requests` — starts where the user
starts, ends where the user cares:

1. `GET /?post_type=product` — shop archive lists the seeded products; first `data-product_id` scraped.
2. `POST /?wc-ajax=add_to_cart` — cart fragments returned; `wp_woocommerce_session_*` cookie set (guest session).
3. Cart URL taken from the mini-cart fragment's "view cart" link → `GET` cart page → checkout link followed.
4. `GET` checkout page → `woocommerce-process-checkout-nonce` scraped from the form; COD offered.
5. `POST /?wc-ajax=checkout` (billing fields + `payment_method=cod` + nonce) → `{"result":"success"}` with the order-received redirect (order id + `wc_order_…` key).
6. `GET` order-received page renders the order to the customer; `wp wc shop_order get <id>` cross-checks the store record (status `processing`, billing email match).
7. Sink presence via `harness/mailsink.py`: customer confirmation + admin new-order mail; **order number in the mail cross-checked against the store record**.
8. Absence (below), then a full sink-census listing.

Checkout over plain HTTP did **not** resist — first attempt succeeded; the
REST-API fallback allowed by the build plan was not needed.

### Absence anchoring (per the F1 clarification)

The absence window is **anchored to completed-event signals, not timers**: it
*opens* after the order has settled (store record verified + both expected
mails present) **and** cron flush #1 (`wp cron event run --due-now`) has
completed; it *closes* when cron flush #2 completes. `assert_none_new` then
holds census-wide **and** per-address — the `settle=` seconds cover SMTP
delivery latency only, they are not the window. On the cold run flush #1
executed 7 due jobs (first-boot WooCommerce housekeeping) and produced no mail;
flush #2 executed 0 — quiescence under an explicit job trigger.

## The clock story (FIXTURES §2.1, rung 3)

WordPress has no scheduler daemon: **wp-cron runs piggybacked on page hits**
by default, which is nondeterministic for fixtures (jobs fire whenever traffic
happens to arrive). The fixture-grade configuration is `DISABLE_WP_CRON=true`
(set via `WORDPRESS_CONFIG_EXTRA` into `wp-config.php`) plus **explicit
harness triggers**: `wp cron event list` shows the due queue, `wp cron event
run --due-now` fires it — both captured in the transcript. WooCommerce's
Action Scheduler rides the same trigger (its `action_scheduler_run_queue`
runner is itself a WP-Cron event). That is rung 3 of the §2.1 mechanism
ladder: the job code stays the host's; only the trigger moves. (Rung 2
LD_PRELOAD fake time was not attempted here — nothing in this leg's proofs is
clock-gated; a future subscriptions-shaped fixture would revisit rungs 1–2.)

## Seeding proof (FIXTURES §2.3)

One command — `./seed.sh`, a single `wp eval-file /seed/seed-products.php`
pass in the wpcli container — creates 3 product categories × 44 published
virtual products = **132 ≥ 120**, SKU-keyed (`F1-EBK-001`…), names and prices
pure functions of the index. **Wall-time: 16.0 s cold** (13.6 s inside WP),
**2.4 s warm** (idempotent no-op, `skipped=132`). A per-invocation
`wp wc product create` loop was rejected: each CLI call pays a container-spawn
+ WP-boot cost (~1.5–2 s), so 132 products would take ~4 min and prove
nothing extra — the one-pass eval-file is the bulk-seeding shape §2.3 needs.

## Findings / deviations (feed back into `validation/FIXTURES.md`)

1. **New WooCommerce ships block cart/checkout** (Store-API driven, not the
   classic form). This leg pins the **classic shortcode pages**
   (`[woocommerce_cart]` / `[woocommerce_checkout]`, still fully supported) in
   `configure-store.php`, which restores the documented deterministic
   `?wc-ajax=checkout` form path. If a future fixture wants the block
   checkout, that path is also plain HTTP (Store API + nonce header) — noted,
   not needed here.
2. **New stores boot in "coming soon" mode** (WooCommerce 9.1+): the
   storefront is curtained until `woocommerce_coming_soon=no`. Handled in
   `configure-store.php`; without it every front-of-store request bounces.
3. **`wordpress:cli` is Alpine; its `www-data` is uid 82**, while the Debian
   apache image's is uid 33. The wpcli service runs `user: "33:33"` so
   everything it writes (plugins, seeded uploads) stays owned by the uid
   apache serves as. (Known official-image gotcha, now load-bearing here.)
4. **Entrypoint chowns break naive resets**: db/ and html/ become
   container-uid-owned on first boot, so the reset path is the
   container-assisted wipe in `demo.sh --reset` (documented above). A related
   `setup.sh` idempotency bug (unconditional `chmod` after first boot) was
   caught by the warm re-run and fixed with an ownership guard.
5. **Subscriptions story:** WooCommerce Subscriptions is **paid**
   (woocommerce.com) and was NOT installed — no paid, nulled, or mirrored
   copies, ever (licensing rule). `wp plugin search subscriptions` (captured
   in the transcript) shows free wordpress.org stand-ins exist, e.g.
   **`subscriptions-for-woocommerce`** (10 k installs, 88 rating) and
   **`flexible-subscriptions`** (1 k, 92) — a viable free stand-in for a
   future `nst`-shaped fixture. Installing one is optional follow-up work and
   was deliberately not allowed to delay this leg.
6. **Plain permalinks kept** (no `.htaccess`/rewrite dependency): the whole
   flow — archive, wc-ajax endpoints, page URLs, order-received — runs on
   query-var URLs, one less moving part in the fixture.
7. **Order mail is synchronous** on this host (arrives during the checkout
   POST; `demo.py` carries a rung-3 re-wait fallback for deferred-mail hosts,
   which did not trigger).

## What this leg does NOT contain

Per the platform charter: no sealed-corpus fixtures, no labels, no implants,
no credentials or payment-provider material. The store, its products, and its
orders are demo scaffolding proving the platform services only.
