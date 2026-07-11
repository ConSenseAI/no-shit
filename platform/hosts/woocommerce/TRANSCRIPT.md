# TRANSCRIPT — noshit-f1-woocommerce

Verbatim capture of one successful **pristine cold-start** run of the
WooCommerce F1 leg, via the documented reset path (container-assisted wipe of
the durable runtime, then full re-bootstrap from nothing):

    ./demo.sh --reset    # wipe /home/user/fixture-runtime/woocommerce/{db,html}
                         # -> up --wait -> install -> seed -> demo.py -> down

**Result:** all assertions passed, `demo.py` exit code 0, `demo.sh` exit code 0.
**Step timeline:** setup 1 s · up+health 17 s · install 30 s · seed 16 s · proof 26 s — **total 90 s**.
**Seeding wall-time:** **16.0 s** for 132 products across 3 categories in one
command (13.6 s inside WP; the remainder is container spawn + WP boot).
**Captured:** 2026-07-11.
**Host:** Docker 26.1.5, Compose v5.3.1.
**Images:** wordpress:latest @sha256:e36cd332… (WordPress 7.0.1, PHP 8.3.32-apache, 762 MB),
mariadb:lts @sha256:628f228f… (341 MB), wordpress:cli @sha256:f8aeb681… (WP-CLI 2.12.0, 207 MB),
axllent/mailpit:v1.30.4 (34 MB, reused — no new pull).

Run history preceding this capture (same code unless noted): the first-ever
cold run passed end-to-end (exit 0, 91 s); the first warm re-run then exposed a
`setup.sh` idempotency bug (unconditional `chmod` on the html/ dir after the
wordpress entrypoint had chowned it to www-data) — fixed with an ownership
guard; the subsequent warm re-run passed (exit 0, 52 s, seeding `created=0
skipped=132` in 2.4 s, sink census exactly 2 messages). This `--reset` capture
re-proved the cold path on the fixed code.

Sink-census note: the third message in the census below —
`Payment gateway "Cash on delivery" enabled` — is WooCommerce's admin notice
from install time, sent by the **wpcli container** while `configure-store.php`
enabled the gateway. It shows the mu-plugin sink wiring covers every
`wp_mail()` source in the stack (apache **and** CLI), and it sits *before* the
absence window, which is anchored to completed events (order settled + cron
flush #1), not to a timer.

Readability edit only: the repetitive compose lifecycle lines for the
ephemeral `wpcli-run-*` containers (`Creating/Created/Waiting/Healthy`, five
lines per wp-cli invocation) are collapsed; nothing else is altered. No
secrets appear below (.env values are never printed by any script).

```text
[demo] --reset: wiping durable runtime (container-assisted; see header) ...
time="2026-07-11T02:39:44Z" level=warning msg="Warning: No resource found to remove for project \"noshit-f1-woocommerce\"."
[demo] setup: secrets + durable dirs ...
[setup] .env exists — keeping it (pass --force to regenerate)
[setup] durable runtime dirs ready under /home/user/fixture-runtime/woocommerce (db/, html/)
[setup] done.
[demo] starting stack (up -d --wait; healthchecks gate readiness) ...
 Network noshit-f1-woocommerce_internal Creating 
 Network noshit-f1-woocommerce_internal Created 
 Container noshit-f1-woocommerce-mailpit-1 Creating 
 Container noshit-f1-woocommerce-mailpit-1 Created 
 Container noshit-f1-woocommerce-wordpress-1 Creating 
 Container noshit-f1-woocommerce-wordpress-1 Created 
 Container noshit-f1-woocommerce-mailpit-1 Starting 
 Container noshit-f1-woocommerce-db-1 Starting 
 Container noshit-f1-woocommerce-db-1 Started 
 Container noshit-f1-woocommerce-mailpit-1 Started 
 Container noshit-f1-woocommerce-wordpress-1 Starting 
 Container noshit-f1-woocommerce-wordpress-1 Started 
 Container noshit-f1-woocommerce-mailpit-1 Waiting 
 Container noshit-f1-woocommerce-wordpress-1 Waiting 
 Container noshit-f1-woocommerce-mailpit-1 Healthy 
 Container noshit-f1-woocommerce-wordpress-1 Healthy 
[demo] polling app over the published loopback port (event-gated, no blind sleeps) ...
[demo] app answering on 127.0.0.1:8083
[demo] install (idempotent: core + WooCommerce + store config) ...
[install] wp core install (site title/admin creds from .env; --skip-email)
Success: WordPress installed successfully.
[install]   WordPress version: 7.0.1
[install]   Database revision: 61833
[install]   TinyMCE version:   4.9110 (49110-20250317)
[install]   Package language:  en_US
[install] wp plugin install woocommerce --version=10.9.4 --activate (from wordpress.org)
Installing WooCommerce (10.9.4)
Downloading installation package from https://downloads.wordpress.org/plugin/woocommerce.10.9.4.zip...
Unpacking the package...
Installing the plugin...
Plugin installed successfully.
Activating 'woocommerce'...
Plugin 'woocommerce' activated.
Success: Installed 1 of 1 plugins.
[install]   name	status	version
[install]   akismet	inactive	5.7
[install]   hello	inactive	1.7.2
[install]   woocommerce	active	10.9.4
[install]   mailpit-smtp	must-use	
[install] configuring store (USD, no shipping, COD offline gateway, classic checkout)
[install]   store configured: currency=USD country=US:CA shipping=disabled coming_soon=no
[install]   cod gateway: enabled=yes enable_for_virtual=yes
[install]   classic pages: cart_page_id=6 checkout_page_id=7 (shortcode content)
[install] wp plugin search subscriptions (evidence only — nothing installed):
[install]   Success: Showing 5 of 4103 plugins.
[install]   name	slug	rating	active_installs
[install]   Paid Membership Subscriptions &#8211; Effortless Memberships, Recurring Payments &amp; Content Restriction	paid-member-subscriptions	94	10000
[install]   Subscriptions for WooCommerce	subscriptions-for-woocommerce	88	10000
[install]   Flexible Subscriptions	flexible-subscriptions	92	1000
[install]   WooCommerce	woocommerce	90	7000000
[install]   Easy Digital Downloads – eCommerce Payments and Subscriptions made easy	easy-digital-downloads	94	40000
[install] done.
[demo] seeding proof (one pass, wall-time recorded) ...
[seed] one-pass bulk seeding: wp eval-file /seed/seed-products.php
[seed]   seed pass: created=132 skipped=0 elapsed_in_wp=13.6s
[seed]   published products total: 132
[seed]     category e-books    products=44
[seed]     category music      products=44
[seed]     category software   products=44
[seed]   Success: seeding proof: 132 products across 3 categories in one pass
[seed] SEEDING WALL-TIME: 16.0s (one command, incl. container spawn + WP boot)
[demo] running E2 proof (demo.py) ...

==========================================================================
== PHASE 0 — preflight: sink, app, seeding census
==========================================================================
[   0.0s] sink reachable at http://127.0.0.1:8028 (1 message(s) held)
[   0.2s] app serving: GET / -> 200 (73416 bytes)
[   5.2s] seeding census: 132 published products; categories: {'e-books': 44, 'music': 44, 'software': 44}
[   5.2s] PASS  seeding proof holds: 132 products >= 120
[   5.2s] PASS  seeding proof holds: 3 non-empty categories >= 3
[   5.2s] TIMELINE  census: 132 products across 3 categories

==========================================================================
== PHASE 1 — browse + add-to-cart over plain HTTP (user's entry point)
==========================================================================
[   5.5s] PASS  GET /?post_type=product (shop archive) -> 200
[   5.5s] PASS  shop archive lists purchasable products (16 add-to-cart buttons on page 1)
[   5.5s] picking first archive product: product_id=12
[   5.5s] PASS  POST /?wc-ajax=add_to_cart -> 200
[   5.5s] PASS  add_to_cart returned cart fragments (no error)
[   5.5s] PASS  WooCommerce session cookie set over plain HTTP (wp_woocommerce_session_5a2749a...)
[   5.5s] TIMELINE  add-to-cart: product 12 x2 in session cart (plain HTTP)
[   5.5s] cart URL discovered from mini-cart fragment: http://127.0.0.1:8083/?page_id=6
[   5.6s] PASS  GET cart page -> 200
[   5.6s] checkout URL discovered from cart page: http://127.0.0.1:8083/?page_id=7
[   5.6s] TIMELINE  cart page shows the item; checkout link followed (user path)

==========================================================================
== PHASE 2 — checkout form -> nonce scrape -> ?wc-ajax=checkout POST (COD)
==========================================================================
[   5.8s] PASS  GET checkout page -> 200
[   5.8s] PASS  scraped woocommerce-process-checkout-nonce from the checkout form
[   5.8s] PASS  offline COD gateway offered on the checkout form
[   6.4s] PASS  POST /?wc-ajax=checkout -> 200
[   6.4s] PASS  checkout succeeded over plain HTTP: order #145 (wc_order_8XbSt...)
[   6.4s] TIMELINE  CHECKOUT via ?wc-ajax=checkout POST: order #145 placed (guest, COD)

==========================================================================
== PHASE 3 — 'ends where the user cares': order-received page + store record
==========================================================================
[   6.5s] PASS  order-received page renders order #145 to the customer
[   9.1s] store record: id=145 status=processing total=10.14 billing.email=f1-customer-1783737648@noshit.test
[   9.1s] PASS  store order record id matches the checkout redirect
[   9.1s] PASS  COD order settled into offline-gateway status 'processing'
[   9.1s] PASS  store record carries the customer's email
[   9.1s] TIMELINE  order #145 verified in store records (status=processing, total=10.14)

==========================================================================
== PHASE 4 — sink PRESENCE: order mail captured + order number cross-check
==========================================================================
[   9.1s] customer mail: subject='Your NoShit F1 Storefront order has been received!' to=f1-customer-1783737648@noshit.test
[   9.1s] PASS  order-confirmation email reached the customer in the sink (synchronous)
[   9.1s] admin mail: subject='[NoShit F1 Storefront]: New order #145' to=admin@noshit.test
[   9.1s] PASS  customer confirmation body cites order #145 (matches store record)
[   9.1s] PASS  admin new-order subject cites order #145 == store record
[   9.1s] TIMELINE  presence: customer + admin order mail for #145 in sink

==========================================================================
== PHASE 5 — rung-3 clock story: DISABLE_WP_CRON + harness-triggered jobs
==========================================================================
[  10.7s] PASS  DISABLE_WP_CRON=1: page-hit cron OFF (fixture-grade)
[  13.4s] wp cron event list: 11 scheduled hooks; first few:
[  13.4s]     | hook	next_run_relative
[  13.4s]     | recovery_mode_clean_expired_keys	now
[  13.4s]     | wp_privacy_delete_old_export_files	now
[  13.4s]     | wp_delete_temp_updater_backups	now
[  13.4s]     | action_scheduler_run_queue	now
[  13.4s]     | jetpack_clean_nonces	now
[  13.4s]     | jetpack_v2_heartbeat	now
[  13.4s]     | wc_admin_process_orders_milestone	now
[  18.4s] cron flush #1 completed: executed 7 due event(s) under harness control
[  18.4s] PASS  harness-triggered job run completed (wp cron event run --due-now)
[  18.4s] TIMELINE  rung-3: cron flush #1 executed 7 due job(s) — COMPLETED event

==========================================================================
== PHASE 6 — sink ABSENCE: window anchored between completed events
==========================================================================
[  18.4s] window opens NOW: order settled (PH3/PH4) and cron flush #1 completed (PH5)
[  21.0s] cron flush #2 completed: executed 0 due event(s) — closes the window
[  25.0s] PASS  ABSENCE holds census-wide: no unexpected mail between the two completed cron flushes (settle covers delivery latency only)
[  25.5s] PASS  ABSENCE holds per-address: no further mail to f1-customer-1783737648@noshit.test after settle
[  25.5s] TIMELINE  absence window held (opened by settled order + flush #1, closed by flush #2)
[  25.5s] sink census — every message this run produced (newest last):
[  25.5s]     | '[NoShit F1 Storefront] Payment gateway "Cash on delivery" enabled' -> admin@noshit.test
[  25.5s]     | '[NoShit F1 Storefront]: New order #145' -> admin@noshit.test
[  25.5s]     | 'Your NoShit F1 Storefront order has been received!' -> f1-customer-1783737648@noshit.test

==========================================================================
== PHASE 7 — timeline
==========================================================================
    WALL  EVENT
--------------------------------------------------------------------------
    5.2s  census: 132 products across 3 categories
    5.5s  add-to-cart: product 12 x2 in session cart (plain HTTP)
    5.6s  cart page shows the item; checkout link followed (user path)
    6.4s  CHECKOUT via ?wc-ajax=checkout POST: order #145 placed (guest, COD)
    9.1s  order #145 verified in store records (status=processing, total=10.14)
    9.1s  presence: customer + admin order mail for #145 in sink
   18.4s  rung-3: cron flush #1 executed 7 due job(s) — COMPLETED event
   25.5s  absence window held (opened by settled order + flush #1, closed by flush #2)

==========================================================================
== RESULT — F1 WooCommerce bench proofs
==========================================================================
  seeding  : 132 products / 3 categories (wall-time in seed.sh output)
  checkout : plain-HTTP ?wc-ajax=checkout (scraped nonce + session cookie) -> order #145
  presence : customer + admin order mail in sink, order number cross-checked
  absence  : census-wide + per-address, anchored between completed cron flushes
  clock    : DISABLE_WP_CRON=true; jobs fire only via wp cron event run --due-now (rung 3)
[  25.5s] ALL ASSERTIONS PASSED in 25.5s wall time (sink now holds 3 message(s))

[demo] ---- step timeline (wall seconds) ----
[demo]   setup    : 1s
[demo]   up+health: 17s
[demo]   install  : 30s
[demo]   seed     : 16s
[demo]   proof    : 26s
[demo]   total    : 90s
[demo] demo.py exit code: 0

[demo] tearing down (scoped: noshit-f1-woocommerce down; durable data preserved) ...
 Container noshit-f1-woocommerce-wordpress-1 Stopping 
 Container noshit-f1-woocommerce-wordpress-1 Stopped 
 Container noshit-f1-woocommerce-wordpress-1 Removing 
 Container noshit-f1-woocommerce-wordpress-1 Removed 
 Container noshit-f1-woocommerce-mailpit-1 Stopping 
 Container noshit-f1-woocommerce-db-1 Stopping 
 Container noshit-f1-woocommerce-db-1 Stopped 
 Container noshit-f1-woocommerce-db-1 Removing 
 Container noshit-f1-woocommerce-db-1 Removed 
 Container noshit-f1-woocommerce-mailpit-1 Stopped 
 Container noshit-f1-woocommerce-mailpit-1 Removing 
 Container noshit-f1-woocommerce-mailpit-1 Removed 
 Network noshit-f1-woocommerce_internal Removing 
 Network noshit-f1-woocommerce_internal Removed 
```
