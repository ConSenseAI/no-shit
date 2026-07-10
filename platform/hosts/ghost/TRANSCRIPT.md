# TRANSCRIPT — Ghost + Stripe test-clock leg (F0)

One successful, verbatim run. Captured **2026-07-10** (UTC). The Stripe key is
masked as `rk_test_***` everywhere by the tooling itself (it never reaches the
terminal, logs, or this file). Stripe sandbox account: `acct_***` (test mode).

- **Host images:** `ghost:5-alpine` (634 MB, digest `sha256:a0506f3f…48bdb5`),
  `axllent/mailpit:v1.21.8` (29.6 MB).
- **Ghost:** development mode + sqlite (no MySQL for F0).
- **Demo wall-clock:** **23 s** cold start → proof → Stripe cleanup → teardown.
- **Result:** exit 0. Floor (Stripe clock mechanics) + target (Ghost member +
  mail sink) both green; the Stripe **subscription lifecycle is BLOCKED** by the
  restricted key's scope (test-clock-only) — see README "Scope denials".

---

## A. Key scope probe (`stripe-clockctl.py doctor`)

```
[00:16:05] DOCTOR: probing restricted-key scopes (test mode)
[00:16:05]   [DENY] read products
[00:16:05]   [DENY] read prices
[00:16:05]   [DENY] read customers
[00:16:05]   [DENY] read subscriptions
[00:16:06]   [DENY] read invoices
[00:16:06]   [DENY] read events
[00:16:06]   [DENY] read payment_methods
[00:16:06]   [ok  ] read test_clocks
[00:16:07]   [ok  ] create test_clock -> clock_1TrS6tAe1QHeexVrQKFvWMAa
[00:16:07]   [ok  ] delete test_clock -> clock_1TrS6tAe1QHeexVrQKFvWMAa
[00:16:07] DOCTOR: 7 scope denial(s): read products, read prices, read customers,
          read subscriptions, read invoices, read events, read payment_methods
```

The only granted scope is **Test Clocks (read + write)**. Everything the
subscription lifecycle needs — products, prices, customers, subscriptions,
invoices, events, payment methods — is denied.

---

## B. Cold-start demo (`./demo.sh`)

```
### cold-start demo run 2026-07-10T00:14:42Z

======================================================================
  1. UP  (docker compose, project noshit-f0-ghost)
======================================================================
 Container noshit-f0-ghost-mailpit  Healthy
 Container noshit-f0-ghost-app      Healthy

======================================================================
  2. PROVE — Stripe sandbox test-clock cycle (floor)
======================================================================
[00:14:49] Detecting key capability ...
[00:14:50]   capability: customers=no, subscriptions=no, invoices=no, events=no, test_clocks=yes
[00:14:50] MODE: CLOCK-MECHANICS (key is test-clock-only)  run_id=1783642490
[00:14:50] The subscription lifecycle is BLOCKED by key scope (see README).
[00:14:50] STEP 1  create test clock frozen at T0
[00:14:50]   [PASS] clock created and 'ready'
[00:14:50]   [PASS] frozen_time == T0 (2026-07-10 00:14 UTC)
[00:14:50]   [PASS] advance step T0+6d within <=2-interval cap
[00:14:50] STEP  advance -> T0+6d
[00:14:53]   [PASS] clock 'ready' after advance to T0+6d
[00:14:53]   [PASS] frozen_time landed exactly at T0+6d (2026-07-16 00:14 UTC)
[00:14:53]   [BLOCKED] subscription fact @ T0+6d: trial_will_end notice would fire (T0+5d, 3d before trial end)
[00:14:53]   [PASS] advance step T0+2d1h within <=2-interval cap
[00:14:53] STEP  advance -> T0+8d1h
[00:14:56]   [PASS] clock 'ready' after advance to T0+8d1h
[00:14:56]   [PASS] frozen_time landed exactly at T0+8d1h (2026-07-18 01:14 UTC)
[00:14:56]   [BLOCKED] subscription fact @ T0+8d1h: trial would convert -> active; invoice finalized + charged
[00:14:56]   [PASS] advance step T0+30d within <=2-interval cap
[00:14:56] STEP  advance -> T0+38d1h
[00:14:59]   [PASS] clock 'ready' after advance to T0+38d1h
[00:14:59]   [PASS] frozen_time landed exactly at T0+38d1h (2026-08-17 01:14 UTC)
[00:14:59]   [BLOCKED] subscription fact @ T0+38d1h: cancel_at_period_end -> canceled at the boundary
[00:14:59] STEP  forward-only invariant: attempt a backward advance (must reject)
[00:14:59]   [PASS] backward advance rejected (forward-only invariant enforced)

==========================================================================
  VIRTUAL-TIME TIMELINE  (simulated clock, not wall time)
==========================================================================
  position   sim UTC            observation
  ----------------------------------------------------------------------
  T0         2026-07-10 00:14   clock frozen at T0
                                  -> would create: customer + 8-day-trial sub (4242 card)  [BLOCKED: scope]
  T0+6d      2026-07-16 00:14   clock at T0+6d
                                  -> trial_will_end notice would fire (T0+5d, 3d before trial end)  [BLOCKED: scope]
  T0+8d1h    2026-07-18 01:14   clock at T0+8d1h
                                  -> trial would convert -> active; invoice finalized + charged  [BLOCKED: scope]
  T0+38d1h   2026-08-17 01:14   clock at T0+38d1h
                                  -> cancel_at_period_end -> canceled at the boundary  [BLOCKED: scope]
==========================================================================
[00:14:59] RESULT: 12/15 clock assertions passed (wall 9.7s)
[00:15:00]   deleted clock clock_1TrS5eAe1QHeexVrhT6wKNt1

======================================================================
  3. PROVE — Ghost membership + mail-sink (target)
======================================================================
[00:15:00] GHOST MEMBERSHIP + MAIL-SINK PROOF (target side; Stripe-decoupled)
[00:15:00]   member under test: f0-member-1783642500@f0-ghost.test
[00:15:01]   Ghost is serving
[00:15:01] STEP 1  ensure owner setup
[00:15:01]   performing first-run owner setup
[00:15:02] STEP 2  checkpoint sink, then POST member signup (magic-link API)
[00:15:02]   [PASS] signup accepted by Ghost (HTTP 201)
[00:15:02] STEP 3  assert signup email arrives in this leg's Mailpit sink
[00:15:02]   [PASS] signup email captured in Mailpit sink
[00:15:02]   [PASS] email is the signup/confirm mail (subject: '🙌 Complete your sign up to No Shit F0 Ghost!')
[00:15:02] STEP 4  follow the magic link (user 'clicks' it)
[00:15:02]   [PASS] magic link present in the email body
[00:15:02]   magic link: http://localhost:2368/members/?token=***&action=signup
[00:15:03]   [PASS] magic link followed (HTTP 200)
[00:15:03] STEP 5  assert member state now exists in Ghost (Members API)
[00:15:03]   [PASS] Ghost returns a stored member for the signed-in session
[00:15:03]   [PASS] member record matches the signup email (f0-member-1783642500@f0-ghost.test)
[00:15:03]   [PASS] member has a Ghost-assigned uuid (a675a4af-41ed-4956-88c9-97da99d3dce5)
[00:15:03]   [PASS] member is a free (unpaid) member
[00:15:03] RESULT: 9/9 assertions passed (wall 2.7s)

======================================================================
  4. Stripe cleanup — delete any tool-owned test clocks
======================================================================
[00:15:03]   found 0 tool-owned clock(s)

======================================================================
  5. DOWN  (scoped teardown: down -v on noshit-f0-ghost only)
======================================================================
 Container noshit-f0-ghost-app      Removed
 Container noshit-f0-ghost-mailpit  Removed
 Volume    noshit-f0-ghost_ghost-content  Removed
 Network   noshit-f0-ghost_f0ghost  Removed

======================================================================
  DEMO COMPLETE — wall 23s — exit 0
======================================================================
  All attainable assertions PASSED.

real	0m23.254s
```

*(Docker's per-line "Creating/Starting/…" progress and repeated INFO log lines
trimmed for readability; assertion lines and the timeline are verbatim.)*

---

## C. What a properly-scoped key would add

The same `./demo.sh` auto-detects a subscription-capable key and runs the FULL
lifecycle instead of the clock-mechanics proof — no code change. The `[BLOCKED]`
lines above become live assertions: `trialing` at T0+6d, a `trial_will_end`
event, `active` + a `$12.00` **paid** invoice at T0+8d1h, and `canceled` at the
period boundary with no further charge.


---

## Run 2 — 2026-07-10 (re-scoped key): FULL LIFECYCLE, 9/9

Operator re-scoped the same restricted key (customers, subscriptions, invoices,
events, products, prices now granted). `stripe-clockctl.py full-cycle`
auto-selected FULL LIFECYCLE mode, verbatim result (key masked):

```
MODE: FULL LIFECYCLE (key has subscription scope)  run_id=1783644568
  [PASS] subscription starts 'trialing' (got trialing)
  [PASS] trial_end == T0+8d (2026-07-18 00:49 UTC)
  [PASS] still trialing at T0+6d (trialing)
  [PASS] trial_will_end event observed
  [PASS] converted to active (active)
  [PASS] a finalized+paid invoice exists (1)
  [PASS] conversion charge == $12.00 ($12.00)
  [PASS] canceled at boundary (canceled)
  [PASS] no extra charge after cancel (1)

  position   sim UTC            observation
  T0         2026-07-10 00:49   clock frozen; subscription created
  T0+6d      2026-07-16 00:49   trial_will_end window crossed -> event evt_1TrSdKAe1QHeexVrNMtQFY87
  T0+8d1h    2026-07-18 01:49   trial converted -> active; invoice in_1TrSdOAe1QHeexVrXWx4Fdng paid $12.00
  T0+39d1h   2026-08-18 01:49   period boundary passed; cancellation honored — no further charge

RESULT: 9/9 assertions passed (wall 31.1s)
FULL LIFECYCLE proven on the Stripe sandbox — floor + billing target met.
CLEANUP: deleted test clock (cascades customers + subscriptions)
```

Tool change with this run: `_lifecycle_proof` now populates the `--json-log`
evidence file (it previously only did so in clock-mechanics mode).
