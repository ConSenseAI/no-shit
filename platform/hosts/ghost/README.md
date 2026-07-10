# Ghost + Stripe test-clock leg (F0)

The Stripe-side leg of the F0 platform proof (see [`../../README.md`](../../README.md)
and [`validation/FIXTURES.md`](../../../validation/FIXTURES.md) §2.1 / §9). It
proves the **virtual-clock** service (FIXTURES §2.1 rung 1) on the Stripe side
and the **messaging-capture** service (§2.2) on the Ghost side, in minutes of
wall time, self-cleaning and re-runnable from a cold start.

Compose project: **`noshit-f0-ghost`**. Host ports: Ghost **2368**, Mailpit UI
**8027** / SMTP **1027**. Databases are never host-published.

---

## TL;DR — what was achieved

The provided sandbox restricted key (`rk_test_***`, account `acct_***`) is
**test-clock-only**: it grants read+write on Test Clocks and is **denied on
everything else** (products, prices, customers, subscriptions, invoices, events,
payment methods, webhooks, account). That scope wall — not the documented clock
caps — is the binding constraint on this leg.

| Deliverable | Target | Achieved with this key |
|---|---|---|
| **Floor** — Stripe test-clock **mechanics** (frozen T0, forward-only advances landing the 8-day-trial script, poll-to-ready, forward-only invariant, delete-cascade) | full | **YES — proven** (12/15 assertions; 3 subscription facts BLOCKED) |
| **Floor** — Stripe **subscription lifecycle** (customer + trial sub + trial_will_end + invoice + charge + cancel) | full | **BLOCKED by key scope** — code-complete & auto-runs on a scoped key |
| **Target** — Ghost **membership + mail sink** (signup → mail in Mailpit → member state) | full | **YES — proven** (9/9 assertions) |
| **Target** — Ghost **billing coupling** (Stripe tiers/checkout inside Ghost) | full | **BLOCKED by key scope** (Ghost connect needs the denied scopes) |

**Honest bottom line:** with *this* key, neither the full floor nor the full
target is attainable — the subscription/billing half of both is walled off by
scope. What *is* attainable is proven green on both sides, and the harness is
complete and validated up to the scope boundary: **drop in a subscription-scoped
key and the same `./demo.sh` proves the full lifecycle with no code change.**

Demo wall-clock: **23 s** cold start → proofs → Stripe cleanup → teardown.
See [`TRANSCRIPT.md`](TRANSCRIPT.md) for a verbatim run.

---

## Run it

```bash
cp .env.example .env          # then paste a real rk_test_… (or sk_test_…) key
./setup.sh                    # checks prereqs, ensures pinned images, probes key scopes
./demo.sh                     # up → prove → timeline → Stripe cleanup → down   (exit≠0 on failure)
./demo.sh --keep              # same, but leave the stack running (Ghost :2368, Mailpit :8027)
```

Point tools individually:

```bash
python3 stripe-clockctl.py doctor            # print the scope map
python3 stripe-clockctl.py full-cycle        # auto: lifecycle (scoped key) | clock-mechanics
python3 stripe-clockctl.py full-cycle --require-full   # exit≠0 if lifecycle scopes are absent
python3 stripe-clockctl.py cleanup           # delete any tool-owned test clocks
python3 ghost_prove.py                       # Ghost member+mail proof (needs the stack up)
```

## What it proves

- **`stripe-clockctl.py` (floor).** Talks to the real Stripe sandbox. It probes
  the key, then runs whichever proof the key supports:
  - *Full lifecycle* (subscription-scoped key): clock at T0 → customer +
    8-day-trial subscription (4242 card `pm_card_visa`) → advance to T0+6d
    (`customer.subscription.trial_will_end`, fired at T0+5d) → advance to
    T0+8d+1h (trial ends, invoice finalized + **$12.00 paid**) → cancel at the
    period boundary (no further charge). Deletes the clock (cascades). Self-cleaning.
  - *Clock mechanics* (this key): the same T0→T0+6d→T0+8d+1h→T0+38d+1h script
    against a bare clock, asserting each advance lands its exact `frozen_time`,
    that advancement is async (poll-to-ready), that steps stay within the
    ≤2-interval cap, and that the **forward-only invariant** is enforced
    (a backward advance is rejected). Every position is annotated with the
    subscription fact it *would* prove, marked `[BLOCKED: scope]`.
- **`ghost_prove.py` (target).** An acceptance test a user could have written:
  member **signup** (public magic-link API) → the signup email is **captured in
  this leg's Mailpit sink** → follow the magic link (the user "clicks" it) →
  Ghost holds the **member as a stored record** (verified via the Members API,
  the member's own authenticated view). Uses the shared
  [`harness/mailsink.py`](../../harness/mailsink.py) pointed at Mailpit :8027.

## Scope denials encountered (record for FIXTURES)

`GET/POST` on account `acct_***`, restricted key `rk_test_***`. Only Test
Clocks are permitted:

| Resource | Result | Scope Stripe named as required |
|---|---|---|
| `test_helpers/test_clocks` (read + write) | **OK** | — |
| `products` (read / write) | 403 | `product_read` (+`feature_read`) / `product_write` (+`feature_write`) |
| `prices` (read / write) | 403 | `price`/`plan_read` / `plan_write` |
| `customers` (read / write) | 403 | `customer_read` / `customer_write` |
| `subscriptions` (read) | 403 | `subscription_read` |
| `invoices` (read) | 403 | `invoice_read` |
| `events` (read) | 403 | `event_read` |
| `payment_methods`, `payment_intents`, `setup_intents`, `charges`, `refunds`, `checkout/sessions`, `subscription_items`, `plans`, `coupons` (read) | 403 | respective `*_read` |
| `account` (read) — Ghost connect validation | 403 | `accounts_kyc_basic_read` |
| `webhook_endpoints` (write) — Ghost members webhook | 403 | `webhook_write` |

To run the **full** floor + Ghost billing coupling, provision the restricted key
with (at minimum): `product_read/write`, `feature_read/write`, `plan_read/write`,
`customer_read/write`, `subscription_read/write`, `invoice_read`, `event_read`,
`payment_method_read/write`, and — for Ghost — `webhook_write` +
`accounts_kyc_basic_read`. Or use an unrestricted `sk_test_…` in the harness
(the harness is out-of-artifact per FIXTURES §1 rule 5, so key breadth there
does not touch fixture realism).

## Deviations & findings for FIXTURES §2.1 / §2.2

1. **The binding Stripe risk is key *scope*, not the clock caps.** FIXTURES §2.1
   assumes test clocks ride subscription lifecycles; that needs the ~10 scopes
   above, not just test-clock scope. Make key-scope provisioning an explicit F1
   build-item and pre-flight check (this leg's `doctor` is that check).
2. **`stripe listen` (CLI webhook forwarding) was not used.** The engine-side
   facts need no webhooks — polling the clock object to `ready` and the events
   endpoint is the event path. Webhooks matter only for *Ghost member state
   riding billing*; with `event_read`/`webhook_write` denied that path is moot
   here. Keep the `stripe/stripe-cli` sidecar **optional** (and note it refuses
   some restricted keys); it was not pulled (saves ~50 MB of scarce disk).
3. **Ghost self-hosted Stripe = direct-key mode and is admin-2FA-gated.** Ghost 5
   gates admin-session login behind an emailed 6-digit code (`Needs2FAError`).
   That code itself lands in the sink — a bonus §2.2 artifact — but any
   automation driving Ghost *admin* (to set Stripe keys/tiers) must complete the
   2FA. Member-state assertions should use the **Members API** (no 2FA), as this
   leg does.
4. **Host-identity skew is a real drift risk (generalizes §2.1's timestamp/host
   skew note).** Ghost scopes member magic-links and the `ghost-members-ssr`
   cookie to its configured `url` host. Harness HTTP must use the *same* host
   string (`localhost`), not `127.0.0.1`, or the session silently fails (204).
   Record alongside the TLS-far-future and engine/app clock-skew risks.
5. **Ghost dev + sqlite is sufficient for F0** ("Stripe not configured -
   skipping migrations" — members boot without Stripe). Production-parity
   **MySQL is an F1 item** (disk was too tight here: ~2.3 GB free).
6. **Minor:** a *bare* test clock (no subscription attached) accepted a `+3yr`
   advance *request* at the API layer, though docs cap bare advances at ≤2yr;
   the ≤2-billing-interval cap only bites with a subscription attached. Not
   exercised by the proof (all advances ≤30d). Also: **delete/modify during an
   in-flight advance returns HTTP 429 "advancement underway"** — always
   poll-to-`ready` before mutating (the tooling does).

## Files

| File | Role |
|---|---|
| `docker-compose.yml` | Ghost (dev+sqlite, pinned by digest) + Mailpit (pinned v1.21.8), project `noshit-f0-ghost` |
| `setup.sh` | prereq checks, pinned-image ensure, Stripe scope probe |
| `stripe-clockctl.py` | capability-adaptive Stripe test-clock proof (floor); masks the key everywhere |
| `ghost_prove.py` | Ghost membership + mail-sink proof (target); reuses `harness/mailsink.py` |
| `demo.sh` | deterministic orchestrator; `--keep`; nonzero exit on failed assertion |
| `.env.example` | key template (`.env` is gitignored; never commit a real key) |
| `TRANSCRIPT.md` | one verbatim successful run, key masked, wall-clock duration |

## Image sizes / footprint

- `ghost:5-alpine` — **634 MB** (digest `sha256:a0506f3f…48bdb5`)
- `axllent/mailpit:v1.21.8` — **29.6 MB** (already local)
- Disk after a full cold demo (up → prove → `down -v`): **~2.3 GB free**.
  `down -v` removes the sqlite content volume, so the leg leaves no residue.

## Key handling

The key lives only in gitignored `.env` (mode 600), is read directly by the
Python tools, and is **never** passed into the Ghost container, echoed, logged,
or committed. All tool output runs through a `mask()` that redacts
`rk_/sk_/pk_/whsec_` tokens (including inside error/exception text) to
`rk_test_***`. On the last day of the sandbox account, `stripe-clockctl.py
cleanup` removes any tool-owned clocks; the demo already deletes its clock
(cascading customers/subscriptions) on every run unless `--keep`.
