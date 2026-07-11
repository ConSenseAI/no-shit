# noshit-f1-listmonk

F1 platform-proof, **Listmonk leg** — proving the platform's **messaging-capture**
and **bulk-seeding** services on a new host, and the **per-address absence
assertion** that clean unsubscribe verdicts depend on.

Listmonk is on the bench for **`no-dark-patterns` (ndp)** and **`no-lock-in` (nli)**
— consent, unsubscribe-parity, and churn-survey surfaces (FIXTURES §3 host
assignments). This leg is public platform/demo code (Apache-2.0): a clean-deploy
fixture host, **no study fixtures, no labels, no implants**.

A self-contained docker-compose stack with a deterministic `demo.sh` that brings
the stack up, seeds ≥200 subscribers, drives two real campaigns through the app's
own API + public unsubscribe flow, and asserts presence **and** per-address
absence against a Mailpit sink — then tears down, leaving the durable data on
disk. A captured run is in [`TRANSCRIPT.md`](./TRANSCRIPT.md) (seed 200 in 1.19 s;
proof 10.5 s; total incl. up/seed/teardown 33 s).

## What this leg proves

| Platform service (FIXTURES §2) | Proven here | How |
|---|---|---|
| **§2.2 — messaging capture + absence monitoring** (O-2, the `msg` channel) | ✓ | Every campaign message lands in this leg's Mailpit (the msg-channel census); a **per-address absence** window (`checkpoint` → `assert_none_new`, `harness/mailsink.py`) holds across a second campaign. `MP_MAX_MESSAGES=0` keeps retention unbounded while the window is open. |
| **§2.3 — state seeding / bulk content** (O-8) | ✓ | The per-host seeding API registers **200 subscribers in one deterministic pass** (`member-NNN@fixture.test`, 1.19 s / 168-per-second on a cold DB) — the "hundreds-per-collection" bulk-content shape. |

### The criterion shapes it rehearses

- **ndp check 6 — consent-withdrawal / unsubscribe parity** (`viol-syn-unsubscribe-maze`;
  GDPR Art. 7(3) "as easy to withdraw as to give"). The round-trip here is the
  *clean* pole: a subscriber unsubscribes in **one action** (a single form POST to
  the address in their own campaign mail), and the decline is **honored and
  persisted** — the very next campaign reaches everyone *except* them. A dark-pattern
  fixture would obstruct that path or quietly re-subscribe; the platform proves we
  can *measure* either outcome.
- **nli — residual messaging / "deleted (unsubscribed) means silent"** ("no
  post-deletion marketing"; §7.1 window registry, *residual messaging, 9d+*). The
  per-address absence assertion **is** the residual-messaging measurement: after the
  exit action, **no further mail** to that address across the following window. O-2's
  point exactly — *clean verdicts are absence verdicts, and a missed message is a
  false-PASS path* — so absence is a first-class, cited artifact, not an afterthought.

## Run it

Prerequisites: Docker + Compose via the `sg docker` wrapper this machine uses,
`python3` (stdlib only), `openssl`. Then:

```bash
cd platform/hosts/listmonk
./demo.sh                 # up --wait -> seed -> proof -> down. Exit 0 = all proofs green.
./demo.sh --keep          # same, but leave the stack running (app :9002, sink UI :8029)
./demo.sh --reset         # wipe the durable DB first (cold start), then run
```

`demo.sh` runs `setup.sh` (generates a gitignored `.env` with a random DB
password + random Super Admin password, ensures the durable data dir and images),
starts the stack waiting on compose **healthchecks** (no sleep-as-sync), runs
`seed.py` then `demo.py`, prints a timeline with timings, and tears down scoped to
`-p noshit-f1-listmonk` (never a global prune). The bind-mounted Postgres data is
**preserved** across teardown.

To run just the proof against an already-running stack: `python3 demo.py` (source
`.env` first so the admin credentials are in the environment).

### Durability & reset

The Postgres data is a **bind mount** under `/home/user/fixture-runtime/listmonk/db/`
(durable disk — *not* a named volume, since the docker store here is volatile).
It survives `down`; seeded subscribers and campaigns persist. To wipe and start
cold:

```bash
rm -rf /home/user/fixture-runtime/listmonk/*     # or: ./demo.sh --reset
```

The reset works **without sudo** because the DB container runs as the host uid
(`1000:1000`), so the data files stay host-owned (see deviation #6).

> **Note:** the durable DB is initialized with the `POSTGRES_PASSWORD` (and Super
> Admin) from `.env`. `setup.sh` keeps an existing `.env` and never overwrites it,
> so warm re-runs stay consistent. If you regenerate `.env` (`./setup.sh --force`),
> also reset the DB (`./demo.sh --reset`) — a fresh password can't authenticate
> against a DB initialized with the old one.

## Stack

Compose project **`noshit-f1-listmonk`**. Host ports are loopback-bound
(`127.0.0.1`) and limited to this leg's registry allocation. Postgres is on the
internal network **only** — never host-published (the machine runs a live
Postgres on 5432).

| Service | Image (pinned) | Host port | Notes |
|---|---|---|---|
| `app` | `listmonk/listmonk:v6.2.0` (digest below) | `9002` → 9000 | the app under test; env-only install (no config.toml) |
| `mailpit` | `axllent/mailpit:v1.30.4` | `8029` UI/API, `1029` SMTP | the per-fixture sink (msg-channel census), unbounded retention |
| `db` | `postgres:15-alpine` | **none** | internal only; runs as uid 1000; data bind-mounted to fixture-runtime |

Non-interactive install is driven entirely by env vars (the compose `command` runs
`./listmonk --install --idempotent --yes --config '' && ./listmonk --upgrade --yes
--config '' && ./listmonk --config ''`). The Super Admin is auto-created from
`LISTMONK_ADMIN_USER` / `LISTMONK_ADMIN_PASSWORD` on first install. Only
`.env.example` is committed; the real `.env` is generated locally and gitignored.

### The real flow driven (listmonk v6.2.0)

Scripted against listmonk's **own** API + public surfaces (`seed.py`, `demo.py`):

1. **Seed** — `POST /api/subscribers` × 200 to a single-opt-in public list (`preconfirm_subscriptions: true`).
2. **Campaign #1** — `POST /api/campaigns` (body carries `{{ UnsubscribeURL }}`) → `PUT /api/campaigns/{id}/status {"status":"running"}`; poll to `finished`; assert `to_send == sent == 200` and **200 captured in the sink**.
3. **Unsubscribe round-trip** — pull the target's own campaign email from the sink, extract `{{ UnsubscribeURL }}` (`/subscription/{campUUID}/{subUUID}`), `GET` it (renders the unsub form), `POST` it (empty body → simple unsubscribe), then confirm `subscription_status == "unsubscribed"` via `GET /api/subscribers/{id}`.
4. **Campaign #2 + absence** — a second campaign to the same list; `to_send` drops to **199** (listmonk excludes the unsubscribed member); 199 captured (presence); **0 new to the unsubscribed address** (`assert_none_new` on `to:<addr>`, after the campaign FINISHED).
5. **(optional) double opt-in** — a double-opt-in list: add subscriber → confirmation mail in sink → follow the confirm link → `subscription_status` flips to `confirmed`.

## Image pins & sizes

| Image | Size | Pulled? |
|---|---|---|
| `listmonk/listmonk:v6.2.0` | **32 MB** | **yes — the only new pull** |
| `postgres:15-alpine` | 292 MB | no (reused) |
| `axllent/mailpit:v1.30.4` | 34 MB | no (reused) |

Digest-pinned in `compose.yaml` (verified 2026-07-11):

```
listmonk/listmonk:v6.2.0@sha256:f535d59e14991337a9f2d570273685378ae86b0d7698c3e00da444e3bc205286
```

New disk footprint: **~32 MB** (well under the leg's budget). No source builds.

---

## Deviation record (feeds back into `validation/FIXTURES.md` §2)

What building the Listmonk leg discovered that the doc-level plan did not spell out.
The messaging-service findings (#2, #4) are the load-bearing ones for the bulk build.

### 1. listmonk v6 API auth is session-cookie or API-token — **not** BasicAuth

v6's API middleware honors a `session` cookie *or* an `Authorization: token
user:api_token` header; the legacy "BasicAuth with the admin user/password" was
removed (v3→v4). The clients here `POST /admin/login` (form `username`/`password`)
as the auto-created Super Admin and carry the resulting `session` cookie — which,
being DB-backed, **survives the settings reload** (below). A wrong assumption here
(BasicAuth) would 403 every call.

### 2. SMTP is a **DB-backed setting**, and saving settings triggers a delayed reload

Listmonk's SMTP server list is **not** a config/env value — it lives in DB
settings, edited via `GET`/`PUT /api/settings`. The default seeded SMTP block is an
*enabled, bogus* `smtp.yoursite.com:25`, so campaigns silently fail until it's
repointed. This leg `PUT`s a single enabled `mailpit:1025` block (`auth_protocol:
none`, `tls_type: none`).

**The important part for fixture timing:** a settings save schedules an app reload
**~500 ms later** (`handleSettingsRestart` → `chReload <- SIGHUP`) that **bounces
the HTTP server** ("reloading on signal … HTTP server shut down … http server
started"). A DB-value convergence check passes *before* the bounce, so a client
that proceeds immediately races the bounce and gets `connection reset by peer`
mid-work. `configure_messaging` therefore waits **past** the bounce and requires
`/health` to be *stably up* (several consecutive OKs) before continuing, and the
client retries transient resets. **Feedback:** any fixture that programs listmonk
settings must treat the save as a restart, not a synchronous write — and do all
settings changes **before** seeding/sending, since the reload also refuses to fire
while a campaign is running (it defers with `needs_restart`).

### 3. List subscriber counts come from a **materialized view** (stale)

`list.subscriber_count` and `subscriber_statuses` are served from
`mat_list_subscriber_stats`, a materialized view refreshed on a schedule — so
immediately after seeding they read **stale** (the transcript shows
`subscriber_count=0` right after 200 inserts, and `196 / {confirmed:98}` mid-refresh
on a warm run). **None of the assertions here use the mat view.** The authoritative,
real-time numbers are a campaign's **`to_send`** (a live recipient query computed at
start) and the subscribers-query **`total`** (a live `SELECT count`). **Feedback:**
any fixture that asserts on list membership counts must query real-time, or refresh
the mat view first — the dashboard-style counts lag.

### 4. Sending is asynchronous + rate-limited — **wait for `finished`, not a timer**

Listmonk hands a started campaign to a background worker pool (`app.concurrency`,
`app.message_rate`, `app.batch_size`); mail is **queued and drained over time**, not
sent synchronously on start. A naive "sleep then check the sink" absence assertion
is unsound: mail can be *queued-but-not-yet-sent*. This leg closes the window on an
**event** — it polls `GET /api/campaigns/{id}` to `status == "finished"` (all
recipients drained) **and** waits until the sink count reaches `sent`, *then*
asserts absence. (The fixture also raises `message_rate` so a 200-recipient campaign
drains in ~2 s instead of the default ~20 s; the default 10/s is the platform-visible
throttle to price into live-observation windows.) **Feedback for FIXTURES §2.2:** a
per-address absence window on a listmonk-class sender must be anchored to the
send-completion event, and §7.1's *residual-messaging (9d+)* window must budget for
the sender's own queue latency on top of the virtual-clock script.

### 5. `{{ UnsubscribeURL }}` resolves against `app.root_url` — set it to the reachable host

The unsubscribe link is `{app.root_url}/subscription/{campUUID}/{subUUID}`. The
install default is `http://localhost:9000`, which is unreachable from the host
(the app is published on 9002). This leg sets `app.root_url = http://localhost:9002`
so the link extracted from the captured mail is directly followable. The unsubscribe
itself is a plain `POST` to that URL with an **empty body** (no nonce/CSRF on the
simple-unsubscribe path — `manage` absent ⇒ `UnsubscribeByCampaign`); a `blocklist=true`
field would additionally blocklist the address globally, which this leg deliberately
does **not** do (list-scoped unsubscribe is the parity shape).

### 6. Postgres bind-mount as the host uid + tmpfs socket dir (durability *and* clean reset)

The durable data lives in a **bind mount**, not a named volume (the docker store
here is volatile). To keep the documented `rm -rf` reset working **without sudo**,
the DB container runs as `user: "1000:1000"` so the files stay host-owned. That
means the image's default socket dir `/var/run/postgresql` (owned by the image's
postgres uid) isn't writable, and the entrypoint's bootstrap `psql` fails on it — so
it's backed by a writable **tmpfs** (`mode=1777`); listmonk connects over TCP
(`host: db`) and the healthcheck uses `pg_isready -h 127.0.0.1`, so the socket dir
is immaterial to the app. `PGDATA` is a subdirectory of the mount (the recommended
bind-mount layout).

### 7. Health endpoint: `/health` is public, `/api/health` requires auth

In v6, `/api/health` (and `/api/config`) sit behind the API auth middleware and
return `403 invalid session` unauthenticated. The **public** health endpoint is
`/health` (`{"data":true}`). Both the compose healthcheck and the Python readiness
poll use `/health`.

## Cleanup

Always scoped; never global (never removes images this leg didn't create):

```bash
sg docker -c "docker compose -p noshit-f1-listmonk down"     # data preserved
rm -rf /home/user/fixture-runtime/listmonk/*                 # full reset (optional)
```
