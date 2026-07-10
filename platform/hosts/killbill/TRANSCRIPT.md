# noshit-f0-killbill — captured runs

Verbatim output of successful cold-start runs of `./demo.sh` (FIXTURES §2.1
rung 1 / F0 exit criterion 1). Both runs begin with `docker compose down -v`
and end by tearing the stack down.

- **Host / date:** 2026-07-10, Docker 26.1.5 + Compose v5.3.1, invoked via `sg docker`.
- **Images:** `killbill/killbill:0.24.16`, `killbill/mariadb:0.24`, `axllent/mailpit:v1.21.8`.
- **Virtual origin T0:** `2026-01-15T08:00:00` (fixed → deterministic). 8-day trial,
  `$29.95`/mo evergreen. Every boundary is crossed with an explicit *noon* datetime
  (see README "Deviations" — the date-vs-datetime trap).

Both runs exited `0`. Note the small real-clock drift after a `set` (T0 shows
`08:00:01`, the PHASE event at `08:00:0x`): Kill Bill's test clock keeps ticking
in real time once positioned, so events land a few seconds after the round
number — the reason every boundary is crossed at **noon**, not on the bare date.

---

## Run A — core clock proof: `./demo.sh` — PASS in 73.3s

```
time="2026-07-10T00:15:23Z" level=warning msg="Warning: No resource found to remove for project \"noshit-f0-killbill\"."
 Network noshit-f0-killbill_internal Creating
 Network noshit-f0-killbill_internal Created
 Volume noshit-f0-killbill_dbdata Creating
 Volume noshit-f0-killbill_dbdata Created
 Container noshit-f0-killbill-db-1 Creating
 Container noshit-f0-killbill-mailpit-1 Creating
 Container noshit-f0-killbill-mailpit-1 Created
 Container noshit-f0-killbill-db-1 Created
 Container noshit-f0-killbill-killbill-1 Creating
 Container noshit-f0-killbill-killbill-1 Created
 Container noshit-f0-killbill-db-1 Starting
 Container noshit-f0-killbill-mailpit-1 Starting
 Container noshit-f0-killbill-mailpit-1 Started
 Container noshit-f0-killbill-db-1 Started
 Container noshit-f0-killbill-db-1 Waiting
 Container noshit-f0-killbill-db-1 Healthy
 Container noshit-f0-killbill-killbill-1 Starting
 Container noshit-f0-killbill-killbill-1 Started
 Container noshit-f0-killbill-mailpit-1 Stopping
 Container noshit-f0-killbill-killbill-1 Stopping
 Container noshit-f0-killbill-mailpit-1 Stopped
 Container noshit-f0-killbill-mailpit-1 Removing
 Container noshit-f0-killbill-mailpit-1 Removed
 Container noshit-f0-killbill-killbill-1 Stopped
 Container noshit-f0-killbill-killbill-1 Removing
 Container noshit-f0-killbill-killbill-1 Removed
 Container noshit-f0-killbill-db-1 Stopping
 Container noshit-f0-killbill-db-1 Stopped
 Container noshit-f0-killbill-db-1 Removing
 Container noshit-f0-killbill-db-1 Removed
 Volume noshit-f0-killbill_dbdata Removing
 Network noshit-f0-killbill_internal Removing
 Volume noshit-f0-killbill_dbdata Removed
 Network noshit-f0-killbill_internal Removed
[1/8] Cold start: docker compose down -v && up -d  (project noshit-f0-killbill)
[2/8] Wait for services healthy
  waiting for Kill Bill health at http://127.0.0.1:8080/1.0/healthcheck ...
  Kill Bill healthy.
[3/8] Tenant + catalog
    tenant ready, catalog uploaded
    mail sink reachable, 0 message(s) held at checkpoint
[4/8] Freeze virtual clock at T0 = 2026-01-15T08:00:00
[5/8] Account + test payment method + subscribe
    assert OK: subscription is ACTIVE in TRIAL (state=ACTIVE, phase=TRIAL)
    assert OK: trial invoice #1 totals $0.00
[6/8] Move clock past trial end (PHASE @ 2026-01-23T08:00:00.000Z) -> 2026-01-23T12:00:00
    assert OK: subscription converted to EVERGREEN (state=ACTIVE)
    assert OK: conversion invoice #2 has RECURRING $29.95
    assert OK: payment 1 PURCHASE $29.95 SUCCESS
[7/8] Cancel (END_OF_TERM) and cross the period boundary
    assert OK: cancel is pending at period end 2026-02-23T08:00:00.000Z (state still ACTIVE)
    move clock to period end -> 2026-02-23T12:00:00
    assert OK: entitlement ended (state=CANCELLED)

==========================================================================
VIRTUAL-TIME TIMELINE  (clock moved by the engine, not wall time)
==========================================================================
VIRTUAL TIME (UTC)         ACTION                             EVIDENCE
--------------------------------------------------------------------------
2026-01-15T08:00:00.000Z   set clock to T0                    virtual now = 2026-01-15T08:00:00.000Z
2026-01-15T08:00:06.000Z   subscribe 'standard-monthly' (8-day trial) trial invoice #1 = $0.00; entitlement ACTIVE/TRIAL
2026-01-23T12:00:11.000Z   clock crosses trial end (T0+8d)    invoice #2 RECURRING $29.95; payment #1 PURCHASE $29.95 SUCCESS; phase EVERGREEN
2026-01-23T12:00:12.000Z   cancel subscription (END_OF_TERM)  cancellation scheduled 2026-02-23 (period boundary); entitlement still ACTIVE
2026-02-23T12:00:08.000Z   clock crosses period boundary      entitlement CANCELLED as of 2026-02-23
2026-02-23T12:00:08.000Z   check mail sink                    0 message(s) in sink (no plugin installed — see README)
==========================================================================

PASS — full trial→convert→charge→cancel cycle in 73.3s wall clock (virtual span 2026-01-15 → 2026-02-23).

Tearing down (scoped): docker compose -p noshit-f0-killbill down -v
```

The single `0 message(s) in sink` line is expected for the core run: the mail
sink is up and wired, but the email-notifications plugin is only installed by the
stretch path below.

---

## Run B — with sink coupling: `./demo.sh --with-email` — PASS in 104.6s

Adds the stretch: install the official `email-notifications` plugin, point its
SMTP at the mailpit sink, and assert invoice/payment notices are captured. This
run matches FIXTURES §9's exit test most fully (engine clock **and** sink jobs
under one time script).

```
time="2026-07-10T00:20:17Z" level=warning msg="Warning: No resource found to remove for project \"noshit-f0-killbill\"."
 Network noshit-f0-killbill_internal Creating
 Network noshit-f0-killbill_internal Created
 Volume noshit-f0-killbill_dbdata Creating
 Volume noshit-f0-killbill_dbdata Created
 Container noshit-f0-killbill-mailpit-1 Creating
 Container noshit-f0-killbill-db-1 Creating
 Container noshit-f0-killbill-mailpit-1 Created
 Container noshit-f0-killbill-db-1 Created
 Container noshit-f0-killbill-killbill-1 Creating
 Container noshit-f0-killbill-killbill-1 Created
 Container noshit-f0-killbill-db-1 Starting
 Container noshit-f0-killbill-mailpit-1 Starting
 Container noshit-f0-killbill-db-1 Started
 Container noshit-f0-killbill-db-1 Waiting
 Container noshit-f0-killbill-mailpit-1 Started
 Container noshit-f0-killbill-db-1 Healthy
 Container noshit-f0-killbill-killbill-1 Starting
 Container noshit-f0-killbill-killbill-1 Started
[email-plugin] 1/6 fetch JAR + DDL (cached in ./data)
[email-plugin] 2/6 copy JAR into container + offline KPM install (v0.8.2)
I, [2026-07-10T00:21:03.654558 #126]  INFO -- : Successful installation of /tmp/email-plugin.jar to /var/lib/killbill/bundles/plugins/java/email/0.8.2
Artifact has been retrieved and can be found at path: /var/lib/killbill/bundles/plugins/java/email/0.8.2/email-plugin.jar
[email-plugin] 3/6 load plugin DDL (idempotent: DROP TABLE IF EXISTS)
[email-plugin] 4/6 restart Kill Bill to load the bundle
 Container noshit-f0-killbill-killbill-1 Restarting
 Container noshit-f0-killbill-killbill-1 Started
[email-plugin] 5/6 wait for Kill Bill health
  healthy
[email-plugin] 6/6 tenant event config: skipped (demo.py uploads it after creating the tenant)
[email-plugin] done. SMTP is wired to mailpit:1025 via org.killbill.mail.smtp.* .
 Container noshit-f0-killbill-killbill-1 Stopping
 Container noshit-f0-killbill-mailpit-1 Stopping
 Container noshit-f0-killbill-mailpit-1 Stopped
 Container noshit-f0-killbill-mailpit-1 Removing
 Container noshit-f0-killbill-mailpit-1 Removed
 Container noshit-f0-killbill-killbill-1 Stopped
 Container noshit-f0-killbill-killbill-1 Removing
 Container noshit-f0-killbill-killbill-1 Removed
 Container noshit-f0-killbill-db-1 Stopping
 Container noshit-f0-killbill-db-1 Stopped
 Container noshit-f0-killbill-db-1 Removing
 Container noshit-f0-killbill-db-1 Removed
 Network noshit-f0-killbill_internal Removing
 Volume noshit-f0-killbill_dbdata Removing
 Volume noshit-f0-killbill_dbdata Removed
 Network noshit-f0-killbill_internal Removed
[1/8] Cold start: docker compose down -v && up -d  (project noshit-f0-killbill)
[2/8] Wait for services healthy
  waiting for Kill Bill health at http://127.0.0.1:8080/1.0/healthcheck ...
  Kill Bill healthy.
[2b/8] Install email-notifications plugin (stretch: sink coupling)
  waiting for Kill Bill health at http://127.0.0.1:8080/1.0/healthcheck ...
  Kill Bill healthy.
[3/8] Tenant + catalog
    tenant ready, catalog uploaded
    email-notifications tenant config uploaded (events -> sink)
    mail sink reachable, 0 message(s) held at checkpoint
[4/8] Freeze virtual clock at T0 = 2026-01-15T08:00:00
[5/8] Account + test payment method + subscribe
    assert OK: subscription is ACTIVE in TRIAL (state=ACTIVE, phase=TRIAL)
    assert OK: trial invoice #1 totals $0.00
[6/8] Move clock past trial end (PHASE @ 2026-01-23T08:00:01.000Z) -> 2026-01-23T12:00:00
    assert OK: subscription converted to EVERGREEN (state=ACTIVE)
    assert OK: conversion invoice #2 has RECURRING $29.95
    assert OK: payment 1 PURCHASE $29.95 SUCCESS
    assert OK: 2 email(s) captured in mailpit sink (invoice + payment notices)
[7/8] Cancel (END_OF_TERM) and cross the period boundary
    assert OK: cancel is pending at period end 2026-02-23T08:00:01.000Z (state still ACTIVE)
    move clock to period end -> 2026-02-23T12:00:00
    assert OK: entitlement ended (state=CANCELLED)

==========================================================================
VIRTUAL-TIME TIMELINE  (clock moved by the engine, not wall time)
==========================================================================
VIRTUAL TIME (UTC)         ACTION                             EVIDENCE
--------------------------------------------------------------------------
2026-01-15T08:00:01.000Z   set clock to T0                    virtual now = 2026-01-15T08:00:01.000Z
2026-01-15T08:00:07.000Z   subscribe 'standard-monthly' (8-day trial) trial invoice #1 = $0.00; entitlement ACTIVE/TRIAL
2026-01-23T12:00:11.000Z   clock crosses trial end (T0+8d)    invoice #2 RECURRING $29.95; payment #1 PURCHASE $29.95 SUCCESS; phase EVERGREEN
2026-01-23T12:00:12.000Z   email-notifications -> sink        2 message(s) in mailpit (SMTP -> mailpit:1025)
2026-01-23T12:00:12.000Z   cancel subscription (END_OF_TERM)  cancellation scheduled 2026-02-23 (period boundary); entitlement still ACTIVE
2026-02-23T12:00:08.000Z   clock crosses period boundary      entitlement CANCELLED as of 2026-02-23
2026-02-23T12:00:08.000Z   check mail sink                    5 message(s) in sink (email-notifications plugin active)
==========================================================================

PASS — full trial→convert→charge→cancel cycle in 104.6s wall clock (virtual span 2026-01-15 → 2026-02-23).

Tearing down (scoped): docker compose -p noshit-f0-killbill down -v
```

The sink held **5 messages** by end of run: two `Your recent invoice`
(INVOICE_CREATION for the $0 trial and the $29.95 conversion), one
`Your recent payment` (INVOICE_PAYMENT_SUCCESS), and the notices emitted as the
cancellation took effect at the period boundary — all `to
subscriber@fixtures.local` `from noreply@fixtures.local`, delivered over SMTP to
`mailpit:1025`. The in-flow assertion fires as soon as ≥1 has landed (it caught 2).
