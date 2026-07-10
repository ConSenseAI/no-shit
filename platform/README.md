# Fixture Platform

**Status: F0 proven (2026-07-10).** The first running code in this repository — all four platform services demonstrated across three host legs, every demo deterministic from a cold start and independently re-run by the coordinator before commit.

| Leg | What it proved | Wall time |
|---|---|---|
| `hosts/killbill/` | Full trial→convert→charge→cancel on the engine test clock: $0 trial invoice at T0, $29.95 recurring invoice **charged** when the clock crossed T0+8d, cancel honored at the period boundary — 39 virtual days; plugin invoice/payment mail in the sink (`--with-email`) | ~96 s |
| `hosts/documenso/` | Real signup→verify→delete flow via the app's own endpoints; +31 virtual days in ~1 s (glibc libfaketime sidecar — Documenso itself is musl); post-deletion absence window held via `checkpoint → assert_none_new`; persona round-trip with a scripted +4h virtual delay | ~36 s |
| `hosts/ghost/` | Stripe sandbox test clock: frozen T0, advances landing exact `frozen_time` at +6d/+8d1h/+38d1h, forward-only invariant enforced, delete-cascade cleanup; Ghost member signup→magic-link→stored-member with mail in the sink (9/9) | ~28 s |

Open sub-item: the Stripe **subscription-lifecycle** facts (trial_will_end → invoice charged → cancel) ran as `BLOCKED: scope` — the provided restricted key covers test clocks only. `stripe-clockctl.py` is capability-adaptive: a key with customer/subscription/invoice/event scopes auto-upgrades the same demo to the full lifecycle proof. Ghost on production-parity MySQL is an F1 item. F0's empirical findings are folded into [`validation/FIXTURES.md`](../validation/FIXTURES.md) §2.1–§2.2 (0.1.1).
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
    ghost/            STAGED — Stripe test-clock leg; blocked on a Stripe sandbox key
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
| ghost (staged) | app | 2368 |
| ghost (staged) | Mailpit UI / SMTP | 8027 / 1027 |

**Forbidden:** port **4000** (a live service unrelated to this project runs there — never bind, probe, or interfere with it), plus locally occupied `4040 4369 5100 5200 5432 8766`.

## Run conventions

- Docker group membership isn't in the login session's credentials on this machine; run everything as `sg docker -c "docker compose ..."`.
- Compose project names: `noshit-f0-<leg>` — cleanup is always scoped (`docker compose -p noshit-f0-<leg> down -v`), never global.
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
