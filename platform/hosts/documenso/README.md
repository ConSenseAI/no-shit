# noshit-f0-documenso

F0 platform-proof, **Documenso leg** (the `no-lock-in` / account-deletion shape).
A self-contained docker-compose stack that proves **three of the four F0 exit
criteria** ([`platform/README.md`](../../README.md)) against a real app's real
account-deletion flow, with a deterministic `demo.sh` that runs the whole proof
in seconds and tears itself down.

| F0 criterion | Proven here | How |
|---|---|---|
| 1 — engine-native clock | ✗ (killbill leg) | out of scope for this leg |
| **2 — app/sink coupling + absence window** | ✓ | Documenso signup confirmation lands in Mailpit; a post-deletion absence window holds via `harness/mailsink.py` (`checkpoint` → `assert_none_new`) bracketed across a virtual-clock advance |
| **3 — stack-level fake time** | ✓ (via sidecar) | LD_PRELOAD libfaketime moves an app-side day-30 job across the boundary in seconds; see the **deviation record** below for *where* it landed and why |
| **4 — persona stub** | ✓ | `personas/responder.py` watches the sink for a trigger and replies after a *scripted virtual delay* (explicit step, not wall-clock sleep), round-trip visible in the sink |

## Run it

Prerequisites: Docker + Compose, `openssl`, `python3` (stdlib only), and the
`sg docker` wrapper this machine uses. Then:

```bash
cd platform/hosts/documenso
./demo.sh            # cold start -> proof -> teardown (down -v). Exit 0 = all criteria proven.
./demo.sh --keep     # same, but leave the stack running (app :3600, sink UI :8026)
```

`demo.sh` runs `setup.sh` (generates `.env` + signing cert + faketime control
file into gitignored `data/`), cold-starts the stack, runs `demo.py`, and always
tears down scoped to `-p noshit-f0-documenso` (never a global prune). It exits
nonzero on any failed assertion. A captured run is in [`TRANSCRIPT.md`](./TRANSCRIPT.md)
(proof 8.5 s; total incl. build/up/teardown 36 s).

To run just the proof against an already-running stack: `python3 demo.py`
(note: the fake-time sidecar fires once, so re-running needs a fresh `--keep`
stack or a `down -v` first).

## Stack

Compose project **`noshit-f0-documenso`**. Host ports are loopback-bound
(`127.0.0.1`) and limited to this leg's registry allocation.

| Service | Image (pinned) | Host port | Notes |
|---|---|---|---|
| `documenso` | `documenso/documenso:v2.14.0` | `3600` | app; listens on 3600 in-container (default 3000 never published) |
| `mailpit` | `axllent/mailpit:v1.30.4` | `8026` UI/API, `1026` SMTP | the per-fixture sink (msg-channel census) |
| `database` | `postgres:15-alpine` | **none** | internal network only — never host-published |
| `scheduler` | `noshit-f0-documenso-scheduler:local` | **none** | glibc + libfaketime sidecar (fake-time proof) |

Secrets/cert are generated locally by `setup.sh` into `.env` and `data/` (both
gitignored); only `.env.example` is committed. SMTP is aimed at mailpit with
`MP_SMTP_AUTH_ACCEPT_ANY` so signup mail is captured regardless of auth.

### The real flow driven (Documenso v2.14.0)

Scripted HTTP against Documenso's own endpoints (no browser, no DB shortcuts for
the flow — `seed.py`):

1. `POST /api/auth/email-password/signup` `{name,email,password}` → 201, fires the confirmation email.
2. confirmation email captured in the sink; the verification **token is extracted from the captured email body**.
3. `POST /api/auth/email-password/verify-email` `{token}` → verifies + auto-authorizes (sets the signed `sessionId` cookie).
4. `POST /api/trpc/profile.deleteAccount?batch=1` (SuperJSON, no input) with that cookie → account deleted (confirmed: 0 rows remain).

## Image sizes

| Image | Size |
|---|---|
| `documenso/documenso:v2.14.0` | 1.68 GB |
| `postgres:15-alpine` | 292 MB |
| `python:3.12-slim` (sidecar base) | 119 MB |
| `noshit-f0-documenso-scheduler:local` | 121 MB (base + libfaketime 0.9.10, ~2 MB) |
| `axllent/mailpit:v1.30.4` | 34 MB |

Documenso dominates. No source builds (the only build is the ~2 MB libfaketime
layer on the prebuilt python-slim). `docker system df` at end of run is shared
with a sibling Kill Bill leg building concurrently on the same disk.

---

## Deviation record (feeds back into `validation/FIXTURES.md` §2)

This is the primary deliverable. What F0 discovered that the doc-level plan
assumed differently:

### 1. Fake-time rung — which worked *where*, and why (criterion 3)

**Landed on: rung 2 (LD_PRELOAD libfaketime), but on a glibc *sidecar*, not on
the app-under-test's own container.**

- **Documenso's container is musl/alpine** (`node:22-alpine3.22`; confirmed at
  runtime in the transcript: `NAME="Alpine Linux"`, `/lib/ld-musl-x86_64.so.1`).
  glibc libfaketime **cannot** `LD_PRELOAD` into a musl process — the dynamic
  loader rejects it. So FIXTURES §2.1's phrase *"a shared control file mounted
  across the fixture's containers"* does **not** generalize: you cannot preload
  a glibc libfaketime into every container in the stack. It preloads only into
  glibc containers.
- This is **not** "Documenso has no time-dependent job." It does: Documenso v2's
  server registers a cron scheduler at boot (`jobsClient.startCron()`, e.g. the
  envelope-expiration sweep). The job exists and reads the app clock — the sole
  blocker to driving it with LD_PRELOAD is the **musl base image**.
- **Resolution used:** a minimal glibc sidecar (`sidecar/`, `python:3.12-slim` +
  libfaketime) in the *same stack*, whose day-30 "retention window expired" job
  fires only when its faked clock crosses the boundary. The demo advances the
  faked clock `+31d` by writing a libfaketime control file
  (`data/faketime/faketimerc`, re-read live via `FAKETIME_NO_CACHE=1`); the job
  fires and its purge notice lands in the sink — day 0 → day 31 in ~1 s of wall
  time. Rung 3 (harness-triggered jobs) was **not** needed.

**Feedback for the bulk build:** for any musl/alpine host (Documenso, and most
official Node images), driving the host's *own* scheduler with libfaketime is
impossible. The fixture options are: (a) run the clock-gated job in a glibc
image, (b) fall back to rung 3 (harness fires the host's job code at scripted
virtual times) for musl hosts, or (c) extract the clock-gated behavior to a
glibc sidecar as done here. FIXTURES §2.1's "verify per host at build" caveat
should be sharpened to **"verify the host image's libc; glibc-only for rung 2."**

### 2. What Documenso's flows actually emit (criterion 2)

- **Signup** sends a confirmation email, subject **`"Please confirm your email"`**
  (job `send.signup.confirmation.email`, runs inline under the `local` jobs
  provider). This is the presence half of criterion 2.
- **Account deletion is silent** — `profile.deleteAccount` → `deleteUser` sends
  **no email at all**. This is *ideal* for the absence half: "no further mail to
  the deleted account" holds naturally and meaningfully, because the account is
  gone and nothing more is ever sent. The post-deletion window is asserted with
  `checkpoint` + `assert_none_new` bracketing the virtual advance, exactly the
  FIXTURES §2.2 shape. (The full deletion flow *was* scriptable, so no narrower
  substitution was needed.)

### 3. Auth is not what a NextAuth/tRPC assumption would predict

Documenso **v2** replaced NextAuth with a custom **Hono** auth app at `/api/auth`
issuing **signed** cookies (keyed by `NEXTAUTH_SECRET`). Signup/verify are plain
HTTP POSTs; only account *deletion* is tRPC (SuperJSON transformer). Two gotchas
worth recording for the next scripted host:
- The session cookie is set with `Domain=.localhost`, which Python's `CookieJar`
  refuses to send back to host `localhost` (the "domain needs embedded dots"
  quirk) → the client echoes `Set-Cookie` values manually instead of using a jar.
- `/api/auth/*` rejects requests whose `Origin` header mismatches the webapp URL
  → scripted clients must omit `Origin` (or set it correctly).

### 4. Host tooling: `compose build` needs a newer buildx than installed

This machine's buildx (0.13.1) predates the 0.17.0 that Compose's own `build`
requires, so `compose up --build` fails. Worked around by building the tiny
sidecar with the **classic builder** (`DOCKER_BUILDKIT=0 docker build`) and
consuming the tag in compose. Relevant to any leg that ships a build.

### 5. Certificate handling

Documenso's `/api/health` cert check only `stat`s the file (existence + non-zero
size); it never parses the p12. A present, world-readable (`644`, so the non-root
container user can read the RO bind-mount) self-signed p12 yields health `ok`.
No far-future TLS drift issue arises here: the stack is HTTP-internal and the
`+31d` advance touches only the sidecar clock, not certificate validity — which
matches FIXTURES §2.1's "run HTTP-internal … under a long-validity internal CA"
mitigation.

## Cleanup

Always scoped; never global:

```bash
sg docker -c "docker compose -p noshit-f0-documenso down -v"
```
