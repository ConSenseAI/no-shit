# noshit-f1-twenty

F1 platform-proof, **Twenty CRM leg** — proving the platform's **host bring-up**,
**bulk-seeding**, and **messaging-capture** services on a new, heavier host, and
the **event-anchored absence assertion** that clean "no residual messaging"
verdicts depend on.

Twenty is on the bench as the deliberate **co-location host** (FIXTURES §3): the
`nst` + `ndp` + `nli` study fixtures will live on this same Twenty instance
later, so this leg proves the instance stands up cleanly from cold, takes bulk
records, and emits real outbound mail into a sink — **before** any study content
exists. This is public platform/demo code (Apache-2.0): a clean-deploy fixture
host, **no study fixtures, no labels, no implants**.

A self-contained docker-compose stack (server + worker + Postgres + Redis +
Mailpit) with a deterministic `demo.sh` that brings the stack up from cold, seeds
≥100 companies **and** ≥100 people through Twenty's own signup + data API, drives
a real workspace-invite email into a Mailpit sink, and asserts presence **and**
event-anchored absence — then tears down, leaving the durable data on disk. A
captured run is in [`TRANSCRIPT.md`](./TRANSCRIPT.md).

## What this leg proves

| Platform service (FIXTURES §2) | Proven here | How |
|---|---|---|
| **Host bring-up** (§9 exit test — a fixture host that stands up from cold) | ✓ | Cold `docker compose up --wait`: Postgres 16 + Redis + Mailpit + Twenty **server** (runs migrations + fresh-DB init) + Twenty **worker** (BullMQ queue) all reach healthy; the first workspace is created through Twenty's **own** signup over plain HTTP. |
| **§2.3 — state seeding / bulk content** (O-8) | ✓ | The per-host seeding API creates **≥100 companies AND ≥100 people in one deterministic, batched pass** (`createCompanies` / `createPeople` on the data GraphQL API), verified by reading `totalCount` back. An **API key** is also minted (`createApiKey` → `generateApiKeyToken`) and used for a REST read — the API-host surface Twenty will serve. |
| **§2.2 — messaging capture + absence monitoring** (O-2, the `msg` channel) | ✓ | A real workspace-member **invite** (`sendInvitations`) lands in this leg's Mailpit (the msg-channel census); the emitted link targets `http://localhost:3001` (SERVER_URL correctness). Then an **event-anchored absence** window (`checkpoint` → `assert_none_new`, `harness/mailsink.py`): a never-invited control address receives nothing, and no residual/duplicate mail follows the single invite. `MP_MAX_MESSAGES=0` keeps retention unbounded while the window is open. |

### The criterion shape it rehearses

- **nli — residual messaging / "one deliberate message, nothing after"** (§7.1
  window registry, *residual messaging*). The absence assertion **is** the
  residual-messaging measurement: after a single, deliberate outbound (the
  invite), **no further mail** to that address, and **nothing** to an unrelated
  address — the window anchored on the **invite-delivered event** (`wait_new`
  returned), never a timer. O-2's point exactly: *clean verdicts are absence
  verdicts, and a missed message is a false-PASS path* — so absence is a
  first-class, cited artifact.
- **Co-location host readiness** (§3). Everything here is the substrate the study
  fixtures sit on: a workspace that authenticates over its own endpoints, holds
  hundreds of records, and speaks to a captured mail channel.

## Run it

Prerequisites: Docker + Compose via the `sg docker` wrapper this machine uses,
`python3` (stdlib only), `openssl`. Then:

```bash
cd platform/hosts/twenty
./demo.sh                 # up --wait -> seed -> proof -> down. Exit 0 = all proofs green.
./demo.sh --keep          # same, but leave the stack running (app :3001, sink UI :8030)
./demo.sh --reset         # wipe the durable DB + storage first (cold start), then run
```

`demo.sh` runs `setup.sh` (generates a gitignored `.env` with a random Postgres
password + random `ENCRYPTION_KEY`, ensures the durable data dirs and images),
starts the stack waiting on compose **healthchecks** (no sleep-as-sync), runs
`seed.py` then `demo.py`, prints a timeline with timings, and tears down scoped to
`-p noshit-f1-twenty` (never a global prune). The bind-mounted Postgres data +
server storage are **preserved** across teardown.

> **First boot is slow.** Twenty's server runs DB migrations and provisions
> workspace metadata on the first cold start (a couple of minutes). The
> `--wait-timeout` is generous; warm boots are fast.

To run just the proof against an already-running stack: `python3 demo.py` (it
reads the founder credentials from the durable state file — see below).

### Durability & reset

Durable state is **bind-mounted** under `/home/user/fixture-runtime/twenty/`
(durable disk — *not* named volumes, since the docker store here is volatile):

- `db/` — Postgres 16 data (the seeded workspace).
- `server-local-storage/` — Twenty's `.local-storage` (attachments).
- `captures/` — the CSV export artifact from the demo's nli bonus.
- `seed-state.json` — the founder email + generated password + workspace id
  (mode `0600`), so warm re-runs and `demo.py` log in with the same credentials.
  **Not** in the repo; wiped by `--reset`.

It survives `down`; seeded companies/people persist. To wipe and start cold:

```bash
rm -rf /home/user/fixture-runtime/twenty/*     # or: ./demo.sh --reset
```

The reset works **without sudo** because both the Twenty image (uid 1000) and the
Postgres container (`user: "1000:1000"`) run as the host uid, so the data files
stay host-owned.

> **Note:** the durable DB is initialized with the `POSTGRES_PASSWORD` and the
> `ENCRYPTION_KEY` from `.env`. `setup.sh` keeps an existing `.env` and never
> overwrites it, so warm re-runs stay consistent. If you regenerate `.env`
> (`./setup.sh --force`), also reset the DB (`./demo.sh --reset`).

## Stack

Compose project **`noshit-f1-twenty`**. Host ports are loopback-bound
(`127.0.0.1`) and limited to this leg's registry allocation. **Postgres AND Redis
are on the internal network only — never host-published** (the machine runs a
live Postgres on 5432).

| Service | Image (pinned) | Host port | Notes |
|---|---|---|---|
| `server` | `twentycrm/twenty:v2.20.0` (digest below) | `3001` → 3000 | the app under test; runs migrations + fresh-DB init on boot |
| `worker` | `twentycrm/twenty:v2.20.0` (same) | **none** | `yarn worker:prod` — the BullMQ queue; where async/scheduled jobs run |
| `db` | `postgres:16-alpine` | **none** | internal only; runs as uid 1000; data bind-mounted to fixture-runtime |
| `redis` | `redis:7-alpine` | **none** | internal only; `--maxmemory-policy noeviction` (BullMQ requirement) |
| `mailpit` | `axllent/mailpit:v1.30.4` | `8030` UI/API, `1030` SMTP | the per-fixture sink (msg-channel census), unbounded retention |

### The real flow driven (Twenty v2.20.0)

Scripted against Twenty's **own** API + public surfaces (`seed.py`, `demo.py`).
Twenty scopes its GraphQL by schema — **auth lives on `/metadata`, the data API on
`/graphql`** (see deviation #1):

1. **Bootstrap** (fresh DB, `seed.py`): `signUp(email,password)` → `signUpInNewWorkspace(displayName)` → `getAuthTokensFromLoginToken` → `activateWorkspace(displayName)` → **re-login** for an actor-bearing token (deviation #3).
2. **Seed** (`seed.py`): `createCompanies(data:[…])` × N and `createPeople(data:[…])` × N in batches of 50 to reach ≥120 each; verify by `companies/people { totalCount }`. Then mint an **API key** and use it for a REST read.
3. **User-path entry** (`demo.py`): `getLoginTokenFromCredentials` → `getAuthTokensFromLoginToken` over plain HTTP → assert the token authorizes a real read (GraphQL `totalCount` + `GET /rest/companies`).
4. **Invite → sink** (`demo.py`): `sendInvitations(emails,roleId)` → the "Join your team on Twenty" email lands in Mailpit; assert recipient + subject, and that the `…/invite/<hash>?inviteToken=…` link targets `http://localhost:3001`.
5. **Event-anchored absence** (`demo.py`): anchored on the invite-**delivered** event — a never-invited control address gets **0** mail, and no residual/duplicate mail follows the single invite.
6. **(bonus) CSV export** (`demo.py`): page `GET /rest/companies` (cursor paging) into `captures/companies-<run>.csv`; assert row count == REST `totalCount` ≥ seeded.

## Image pins & sizes

| Image | On-disk size | Pulled? |
|---|---|---|
| `twentycrm/twenty:v2.20.0` | **1.12 GB** | **yes — new pull** (~245 MB compressed) |
| `postgres:16-alpine` | 294 MB | **yes — new pull** (Twenty requires pg16; pg15 not used) |
| `redis:7-alpine` | 39 MB | **yes — new pull** |
| `axllent/mailpit:v1.30.4` | 34 MB | no (reused) |

New disk footprint: **≈1.45 GB** (~0.54 GB compressed pull) — under the leg's
1.8 GB budget. No source builds. Twenty's image is digest-pinned in `compose.yaml`
and `setup.sh` (verified 2026-07-11):

```
twentycrm/twenty:v2.20.0@sha256:1d1c121c56a98fcc365cd8856f605230134958de924619fb1e03af2812c456ae
```

## Clock-story note (F2 planning — no proof required here)

- **libc / base:** the Twenty image is **musl / Alpine** (`node:24.18.0-alpine3.23`,
  Node 24, runs as uid 1000). So it is **not** a straight rung-2 `libfaketime`
  `LD_PRELOAD` candidate: it needs the **glibc-sidecar pattern** (the same
  approach the `documenso` F0 leg used for a musl app), or a musl-built
  libfaketime with its known limitations.
- **Where scheduled jobs run:** the Twenty **server** *registers* cron schedules
  (into Redis/BullMQ) on boot; the **worker** container (`yarn worker:prod`)
  *consumes and executes* them — async email dispatch, sync jobs, workflows.
  **That worker is what a fake clock must reach** in F2 (BullMQ requires Redis
  `noeviction`, set in compose). Migrations/cron-registration are disabled on the
  worker (`DISABLE_DB_MIGRATIONS`/`DISABLE_CRON_JOBS_REGISTRATION=true`) because
  the server already does them.

---

## Deviation record (feeds back into `validation/FIXTURES.md` §2)

What building the Twenty leg discovered that the doc-level plan (and the initial
task assumptions) did not spell out. #1–#3 are the load-bearing ones for anyone
scripting Twenty.

### 1. GraphQL is schema-scoped: **auth is on `/metadata`, data on `/graphql`**

Twenty serves multiple GraphQL schemas at different paths. The **data** API
(`companies`, `people`, `createCompanies`, …) is `/graphql` and requires a
workspace-scoped token. The **auth + admin** surface — `signUp`,
`signUpInNewWorkspace`, `getLoginTokenFromCredentials`,
`getAuthTokensFromLoginToken`, `activateWorkspace`, `getRoles`, `sendInvitations`,
`createApiKey`, `generateApiKeyToken` — is on **`/metadata`** (the `AuthResolver`
is decorated `@MetadataResolver()`). A client that posts auth mutations to
`/graphql` gets `Cannot query field "signUp" on type "Mutation"`. Also:
**introspection and "did you mean" suggestions are disabled for *unauthenticated*
requests** (`useDisableIntrospectionAndSuggestionsForUnauthenticatedUsers`) — they
switch back on once you present a valid token, which is how `seed.py`/`demo.py`
were nailed down against the live image.

### 2. Fresh-instance bootstrap is multi-step, and `signUp` is **one-shot**

There is no single "create admin" call. The first workspace is:
`signUp` (creates a workspace-less user, returns a **workspace-agnostic** token) →
`signUpInNewWorkspace` (Bearer = agnostic token; returns a `loginToken` +
`workspace.id`) → `getAuthTokensFromLoginToken` (→ workspace-scoped token) →
`activateWorkspace` (provisions the Company/Person schema + data source). On this
**single-tenant** instance (`IS_MULTIWORKSPACE_ENABLED=false`), once that first
workspace exists, `signUp` returns `SIGNUP_DISABLED` ("New workspace setup is
disabled") — **every subsequent user must be invited** (`sendInvitations`). So
`seed.py` branches on `checkUserExists(founder)`: absent → full bootstrap; present
→ log in with the saved founder password. (The old `IS_SIGN_UP_DISABLED` flag from
Twenty v0.x is gone; nothing needs setting to *enable* the first signup.)

### 3. The access token must be **re-minted after `activateWorkspace`**

A token obtained from `getAuthTokensFromLoginToken` **before** activation has no
workspace-member/actor context. Data writes with it fail
`Unable to build actor metadata - no valid actor information found in auth
context`, and even reads fail `INVALID_AUTH_CONTEXT`. The fix: after
`activateWorkspace`, **log in again** for a fresh token that carries the actor.
`seed.py` always re-logs-in post-activation before seeding.

### 4. Env-name / version drift (Twenty is now v2.x, not v0.x)

Tags are `twenty/vMAJOR.MINOR.PATCH` (this leg pins `twenty/v2.20.0`). Concretely:
- **`ENCRYPTION_KEY`** is the app secret (`openssl rand -base64 32`); **`APP_SECRET`
  is legacy** (only for instances predating `ENCRYPTION_KEY`) — this leg sets
  `ENCRYPTION_KEY` and leaves `APP_SECRET` unset.
- **`EMAIL_DRIVER` enum is `SMTP` | `LOGGER`, default `LOGGER`** (log-only, silent
  no-send). It **must** be set to `SMTP` explicitly or no mail is delivered — the
  original task assumption of a lowercase `smtp` happens to work (the enum coerces)
  but `SMTP` is the canonical value.
- **`EMAIL_SYSTEM_ADDRESS` was removed** in v2.x; `EMAIL_FROM_ADDRESS` is the
  effective sender. (`SERVER_URL` still drives the links inside invite/reset mail.)
- **`PG_DATABASE_URL`** (a single URL, DB name `default`), `REDIS_URL`,
  `SERVER_URL` are the connection envs — not the split `PG_*` host/port the task
  hinted at (those exist only as compose interpolation defaults).

### 5. `postgres:16-alpine` is sufficient — no spilo, no pgvector

v2.20.0's fresh-DB init creates only `uuid-ossp` and `unaccent` (both in the
stock/alpine Postgres contrib set) plus the `core`/`public` schemas; it does **not**
`CREATE EXTENSION vector` at default init (the historical reason the custom
`twentycrm/twenty-postgres-spilo` image existed — that requirement is gone by
default, and spilo's newest tag is frozen at `v0.43.5`/Mar-2025). FDW extensions
are gated behind `IS_FDW_ENABLED=true`, which this leg does not set. Confirmed
empirically: migrations + init ran clean on `postgres:16-alpine`.

### 6. A fresh workspace ships ~5 sample companies + ~5 sample people

`activateWorkspace` provisions a handful of onboarding sample records. `seed.py`
therefore gates on the live `totalCount` and creates *up to* the target (e.g. it
created 115 to reach 120 companies on the captured run) — idempotent, and always
well above the ≥100 floor.

### 7. Postgres bind-mount as the host uid + tmpfs socket dir (durability + clean reset)

Same pattern as the `listmonk` leg: the durable DB is a **bind mount** (not a named
volume — the docker store here is volatile), the DB container runs as
`user: "1000:1000"` so the `rm -rf` reset works **without sudo**, and the image's
default socket dir `/var/run/postgresql` (owned by the image's postgres uid) is
backed by a writable **tmpfs**; Twenty connects over TCP (`host: db`). The Twenty
image already runs as uid 1000, so its `.local-storage` bind mount is host-owned too.

### 8. The invite link segment is the **workspace invite hash**, not the workspace id

The emitted link is `${SERVER_URL}/invite/<workspaceInviteHash>?inviteToken=<token>`.
The `<…>` path segment is a per-workspace invite hash (a distinct UUID), not the
workspace id — so the demo asserts host + link shape (`http://localhost:3001/invite/…`
with an `inviteToken`), which is what proves `SERVER_URL` correctness.

### 9. CSV export is a frontend feature — the demo exports via the REST API instead

Twenty has no server-side CSV-export endpoint (the UI builds the CSV client-side).
The nli bonus therefore **pages the companies collection via `GET /rest/companies`**
(cursor paging: `?limit=60&starting_after=<endCursor>`, `pageInfo.hasNextPage`) and
writes the CSV itself, asserting the row count equals the REST `totalCount`.

## Cleanup

Always scoped; never global (never removes images this leg didn't create):

```bash
sg docker -c "docker compose -p noshit-f1-twenty down"     # data preserved
rm -rf /home/user/fixture-runtime/twenty/*                 # full reset (optional)
```
