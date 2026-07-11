# noshit-f1-formbricks

F1 platform-proof, **Formbricks leg** — proving the platform's **host bring-up**,
**bulk-seeding**, and **messaging-capture** services on a new host for the
**churn-survey surface**: the exit-survey / cancel-flow questionnaire shape that
`ndp` / `nst` fixtures will later exercise.

Formbricks is on the bench (with Listmonk / Plausible / Keila) for the
**churn/cancellation survey** — a link survey with a required multiple-choice
"why are you leaving?" plus an open-text follow-up, seeded to ≥100 responses and
driven end-to-end from the public survey URL. This is public platform/demo code
(Apache-2.0): a clean-deploy fixture host, **no study fixtures, no labels, no
implants**.

A self-contained docker-compose stack (Formbricks CE + Postgres/pgvector +
Mailpit) with a deterministic `demo.sh` that brings the stack up from cold, seeds
a churn survey + **120 responses through the public display→response API**, and
proves three things over plain HTTP: a **signup→verification-mail round-trip**, a
**user-path (anonymous) survey fill**, and a **response-notification presence +
absence pair**. A captured run is in [`TRANSCRIPT.md`](./TRANSCRIPT.md).

## EE boundary (explicit)

Formbricks' enterprise code lives under **`apps/web/modules/ee/`** (a separate
**Formbricks Enterprise License**, distinct from the AGPLv3 core; **billing** is
under `ee/billing/`). This leg is **community features only**:

- **No** `ENTERPRISE_LICENSE_KEY`, **no** billing configuration, **no** EE-gated
  feature toggles of any kind.
- Everything driven here is core/CE: signup + email verification, the link-survey
  + response model, the management REST API, the public client API, and the
  per-response owner-notification pipeline — none of which import from `ee/`.
- Multi-workspace, SSO/SAML, team RBAC, contacts/segments, quotas, and audit logs
  are EE and are **not** touched. The instance runs single-organization.

## What this leg proves

| Platform service (FIXTURES §2) | Proven here | How |
|---|---|---|
| **Host bring-up** (§9 exit test — a fixture host that stands up from cold) | ✓ | Cold `docker compose up --wait`: Postgres 15 **+ pgvector** + Mailpit + Formbricks (self-migrates 128 Prisma migrations on first boot) all reach healthy; the first user is created through Formbricks' **own** signup over plain HTTP. |
| **§2.3 — state seeding / bulk content** (O-8) | ✓ | The per-host seeding path creates **≥100 churn responses in one deterministic pass** through the **public display→response API the survey widget itself uses**, verified by reading the count back via the management API. A churn link-survey (multiple-choice + open text) is created via the management API; the management API key is minted headlessly. |
| **§2.2 — messaging capture + absence monitoring** (O-2, the `msg` channel) | ✓ | Two real mail flows land in this leg's Mailpit (the msg-channel census): the **email-verification** mail (signup round-trip) and the **per-response owner-notification** mail; both carry host-reachable `http://localhost:3003` links (WEBAPP_URL correctness). Then an **event-anchored absence** window (`checkpoint` → `assert_none_new`, `harness/mailsink.py`): a never-notified control gets nothing, and no residual/duplicate alert follows a single pipeline trigger. `MP_MAX_MESSAGES=0` keeps retention unbounded while the window is open. |

### The criterion shape it rehearses

- **The churn-survey surface** (`ndp`/`nst`). The seeded object is the exit-survey
  pattern itself: a cancellation questionnaire (required MC reason + open text),
  filled from the anonymous public link the way a churning user would, with the
  response landing verified through the owner-facing API. This is the substrate
  `ndp`/`nst` implants will later sit on.
- **Residual messaging / "one deliberate message, nothing after"** (§7.1 window
  registry). The notification absence assertion **is** the residual-messaging
  measurement: after one deliberate owner alert, **no further mail** to that
  owner and **nothing** to an unrelated address — anchored on the
  alert-**delivered** event (`wait_new` returned), never a timer.

## Run it

Prerequisites: Docker + Compose via the `sg docker` wrapper this machine uses,
`python3` (stdlib only), `openssl`. Then:

```bash
cd platform/hosts/formbricks
./demo.sh                 # up --wait -> seed -> proof -> down. Exit 0 = all proofs green.
./demo.sh --keep          # same, but leave the stack running (app :3003, sink UI :8033)
./demo.sh --reset         # wipe the durable DB + uploads first (cold start), then run
```

`demo.sh` runs `setup.sh` (generates a gitignored `.env` with a random Postgres
password + Formbricks' three required secrets, ensures the durable dirs, **builds
the pgvector-enabled Postgres image** from the resident `postgres:15-alpine`,
verifies images), starts the stack waiting on compose **healthchecks** (no
sleep-as-sync), runs `seed.py` then `demo.py`, prints a timeline with timings, and
tears down scoped to `-p noshit-f1-formbricks` (never a global prune). The
bind-mounted Postgres data is **preserved** across teardown.

> **First boot is slow.** Formbricks runs 128 Prisma migrations against the
> pgvector DB on the first cold start (~2–3 minutes). The `--wait-timeout` is
> generous; warm boots are fast (~30 s total).

To run just the proof against an already-running stack: `python3 demo.py` (it
reads the founder credentials + API key from the durable state file; `CRON_SECRET`
must be exported — `set -a; . ./.env; set +a`).

### Durability & reset

Durable state is **bind-mounted** under `/home/user/fixture-runtime/formbricks/`
(durable disk — *not* named volumes, since the docker store here is volatile):

- `db/` — Postgres 15 data (the founder user, org, environment, churn survey, and
  the ≥120 seeded responses).
- `uploads/` — Formbricks local file storage (world-writable; the app runs as uid
  1001 while Postgres runs as the host uid 1000). Not exercised by the
  churn-survey proofs — the durable state the proofs depend on is the DB.
- `seed-state.json` — founder email + generated password + org/project/environment
  ids + the minted **API key** + the survey id (mode `0600`), so warm re-runs and
  `demo.py` reuse the same instance. **Not** in the repo; wiped by `--reset`.

It survives `down`; the seeded survey + responses persist. To wipe and start cold:

```bash
rm -rf /home/user/fixture-runtime/formbricks/*     # or: ./demo.sh --reset
```

The reset works **without sudo** because Postgres runs as `user: "1000:1000"` (the
host uid), so the data files stay host-owned.

## Stack

Compose project **`noshit-f1-formbricks`**. Host ports are loopback-bound
(`127.0.0.1`) and limited to this leg's registry allocation. **Postgres is on the
internal network only — never host-published** (the machine runs a live Postgres
on 5432).

| Service | Image (pinned) | Host port | Notes |
|---|---|---|---|
| `formbricks` | `ghcr.io/formbricks/formbricks:v3.16.1` (digest below) | `3003` → 3000 | the app under test; self-migrates on boot; Redis intentionally omitted |
| `db` | `noshit-f1-formbricks-postgres:15-pgvector` (built local) | **none** | `postgres:15-alpine` + pgvector 0.8.0; internal only; runs as uid 1000; data bind-mounted |
| `mailpit` | `axllent/mailpit:v1.30.4` | `8033` UI/API, `1033` SMTP | the per-fixture sink (msg-channel census), unbounded retention |

### The real flow driven (Formbricks v3.16.1)

Scripted against Formbricks' **own** surfaces (`seed.py`, `demo.py`):

1. **Bootstrap** (`seed.py`, fresh DB): register the founder via the **`createUser`
   server action** over plain HTTP (real signup → verification mail) → mark
   verified → **DB-insert** the organization + project + prod/dev environments +
   owner membership (the org-creation step is itself a server action) → **mint a
   management API key** headlessly by inserting `ApiKey` + `ApiKeyEnvironment`
   (`hashedKey = sha256_hex(key)`, verified against `/api/v1/management/me`).
2. **Seed** (`seed.py`): create the churn **link survey** (`POST
   /api/v1/management/surveys`), then submit **120 responses** in one pass through
   the public **display→response** API (`POST /api/v1/client/{envId}/displays` then
   `.../responses`); verify the count via `GET /api/v1/management/responses`.
3. **Signup round-trip** (`demo.py`): register a fresh user via `createUser` →
   the verification email lands in Mailpit → follow the emitted
   `http://localhost:3003/auth/verify?token=…` link → account made active, proven
   by a successful authenticated NextAuth login (login is gated on email-verified).
4. **User-path fill** (`demo.py`): anonymous `GET /s/{surveyId}` (the public link
   survey) → `display` → `response` through the widget's own endpoints → verify the
   response landed via the management API (count +1).
5. **Notification pair** (`demo.py`): enable the owner's per-response alert, submit
   a response, and **harness-trigger the response pipeline** (`POST /api/pipeline`,
   `CRON_SECRET`) → the owner alert email lands in the sink (presence); then,
   anchored on that delivered event, a never-notified control gets 0 and no
   residual alert follows (absence).

## Image pins & sizes

| Image | On-disk size | Pulled? |
|---|---|---|
| `ghcr.io/formbricks/formbricks:v3.16.1` | **1.15 GB** | **yes — new pull** (the one CE image) |
| `noshit-f1-formbricks-postgres:15-pgvector` | 292 MB (shares the `postgres:15-alpine` base; **~1 MB unique** pgvector delta) | **built local** (base reused) |
| `postgres:15-alpine` | 292 MB | no (reused base) |
| `axllent/mailpit:v1.30.4` | 34 MB | no (reused) |

Net new persistent disk: **≈1.15 GB** (the Formbricks image) + a ~1 MB pgvector
layer — within the leg's 1.2 GB budget. No second DB image was pulled. Formbricks
is digest-pinned in `compose.yaml` and `setup.sh` (verified 2026-07-11):

```
ghcr.io/formbricks/formbricks:v3.16.1@sha256:1cd324d2dc82eb906bf3a03ffc7d679b81d2d0ebdb35173669a68afe84350239
```

## Clock-story note (F2 planning — no proof required here)

- **libc / base:** the Formbricks image is **musl / Alpine 3.21** (`node:22`, runs
  as uid 1001). So it is **not** a straight rung-2 `libfaketime` `LD_PRELOAD`
  candidate: it needs the **glibc-sidecar pattern** (as the `documenso`/`twenty`
  legs used) or a musl-built libfaketime with its known limitations.
- **Where scheduled work runs:** the image runs an **in-container cron**
  (`supercronic` → `/app/docker/cronjobs`) for periodic work (e.g. the
  weekly-summary email). Per-response **owner notifications** run through
  **`/api/pipeline`** — an internal endpoint the app self-calls via `WEBAPP_URL`
  (unreachable in-container, since `WEBAPP_URL` is the host origin), protected by
  `CRON_SECRET`. Both are **harness-triggerable** (FIXTURES rung 3): PHASE 3 of the
  demo drives the pipeline directly with `CRON_SECRET`. A fake clock must reach
  that cron/pipeline process.
- **Native time-windowed behaviors worth F2 attention:** the weekly-summary
  cadence, survey scheduling (`status=scheduled` + `runOnDate`), and response
  recontact windows.

---

## Deviation record (feeds back into `validation/FIXTURES.md` §2)

What building the Formbricks leg discovered that the doc-level plan (and the
initial task assumptions) did not spell out. #1–#4 are the load-bearing ones for
anyone scripting Formbricks.

### 1. Current stable CE requires **pgvector** — the resident `postgres:15-alpine` is extended in place (not a second image)

Formbricks v3.16.1's baked Prisma migrations run `CREATE EXTENSION IF NOT EXISTS
"vector"` (migration `20241017124431_add_documents_and_insights`) and declare
`vector(512)` columns on its AI `Insight`/`Document` tables — pgvector is a **hard
migration-time requirement**, so the app will not boot against a stock Postgres.
The task's "reuse `postgres:15-alpine`" instruction assumed Formbricks runs on
plain Postgres; it does not. Rather than pull the ~430 MB Debian
`pgvector/pgvector:pg15` image (a second DB image, over the leg's disk budget),
`postgres-pgvector.Dockerfile` **builds pgvector 0.8.0 from source against the
resident `postgres:15-alpine`** (its server headers + PGXS ship in the image,
verified) and copies the ~1 MB extension artifacts into a pristine
`postgres:15-alpine` final stage. Every base layer is shared with the resident
image, so net new persistent disk is negligible — the faithful realization of
"reuse `postgres:15-alpine`" given the hard dependency. `setup.sh` builds it
idempotently.

### 2. Current stable is a **multi-service rearchitecture** — this leg pins the last classic single-container CE (v3.16.1)

The newest stable Formbricks (5.x, mid-2026) is **not** a single web container: its
official compose is five services (web + `pgvector` + Valkey + a `hub` API + a
`cubejs` analytics service, with `CUBEJS_API_SECRET` required and Cube listening on
container-internal :4000). That is incompatible with the operator's
`{app + postgres + mailpit}` stack and the disk budget. The lineage is **stable
3.x → (4.x only ever an RC) → 5.x**, so the newest stable *classic single-container*
CE is **v3.16.1** (only `postgres` + `formbricks` services; Redis optional). Note
the **git** tags reach `v3.17.1` but ghcr has **no published CE image** past
`v3.16.1` — v3.16.1 is the newest installable stable CE.

### 3. **Redis is optional** in 3.x (mandatory only from 5.x)

Formbricks 3.16.1 boots and serves with **no `REDIS_URL`** (an in-memory cache /
rate-limit fallback) — confirmed empirically. Redis is therefore omitted, keeping
the leg to the `{app + postgres + mailpit}` shape. (5.x makes `REDIS_URL`
mandatory and bundles Valkey.)

### 4. Signup, org-creation, and email-verification are **Next.js server actions**, not REST — the API-key mint is a direct DB insert

There is no REST signup endpoint. Registration is the **`createUser` server
action**, driven over plain HTTP with a `Next-Action: <id>` header + a React-reply
multipart body (field `"0"` = a single `{name,email,password}` object). The action
id is deterministic for the digest-pinned image (`7fdd8b95…`; `seed.py`/`demo.py`
pin it). `createUser` creates **only** a `User` row (+ sends the verification
mail); the organization/project/environment are created by a *separate* server
action, so this leg **DB-inserts** them directly (their DDL is simple; only
`Organization.billing` needs a real free-tier JSON shape). **API keys are UI-only**
in Formbricks (no CLI/seed mint — confirmed by the maintainers); the documented
headless path is a direct `ApiKey` + `ApiKeyEnvironment` insert with
`hashedKey = sha256_hex(key)` — verified: an `x-api-key` with that hash
authenticates the management API. **Email verification** is likewise a client-side
server action: the emitted `/auth/verify?token=<JWT>` link is real and
host-reachable (the demo follows it over plain HTTP), but its **token consumer** is
a client-invoked action not reachable as a plain endpoint, so the demo confirms
"account active" via the app's data-layer verify **plus a successful authenticated
login** (login is gated on email-verified — the task's permitted "verify via API or
successful authenticated call"). `EMAIL_VERIFICATION_DISABLED=0` turns the
verification mail ON (the shipped compose ships `=1`).

### 5. The public client API is **rate-limited** — disabled for bulk seeding

Formbricks' public client API (displays/responses) has an in-memory rate limiter
that trips partway through a >100-response bulk pass (HTTP 429). `RATE_LIMITING_DISABLED=1`
is set for this fixture — rate limiting is not part of the churn-survey surface
being proven.

### 6. Per-response notifications need the pipeline **triggered** (WEBAPP_URL self-call is in-container-unreachable)

Owner alert emails are sent by the response **pipeline** (`/api/pipeline`, internal,
`CRON_SECRET`-protected). Formbricks self-calls it via `WEBAPP_URL` on response
creation — but `WEBAPP_URL=http://localhost:3003` is the *host* origin and is not
reachable from inside the container (the app listens on :3000 there), so the inline
alert never fires. Keeping `WEBAPP_URL` host-reachable is required for the emailed
links (Proof 1), so the notification proof **harness-triggers** the pipeline with
`CRON_SECRET` — which is exactly the rung-3, harness-triggerable-scheduler shape
F2 will lean on.

## Cleanup

Always scoped; never global (never removes images this leg didn't create):

```bash
sg docker -c "docker compose -p noshit-f1-formbricks down"     # data preserved
rm -rf /home/user/fixture-runtime/formbricks/*                 # full reset (optional)
sg docker -c "docker rmi noshit-f1-formbricks-postgres:15-pgvector"   # the one image this leg built
```
