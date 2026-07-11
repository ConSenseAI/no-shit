# noshit-f1-plausible — F1 bench leg (Plausible Community Edition)

**Status: proven green (2026-07-11).** Cold `./demo.sh --reset` exits 0 from a
wiped disk; warm `./demo.sh` re-runs stay green on per-run-unique identities.

Plausible CE is on the F1 bench (with Listmonk / Keila / Formbricks) for the
platform's **consent / analytics** surfaces. This leg proves the platform's
services on a NEW, two-datastore host — it is PUBLIC platform code (Apache-2.0):
**no study fixtures, no labels, no implants.** What it proves:

| # | Proof | Mechanism |
|---|---|---|
| host bring-up | Plausible CE + **its ClickHouse dependency** + Postgres stand up cold, migrate, and serve | compose `--wait` gated on real healthchecks (`/api/health`, `pg_isready`, CH `/ping`) |
| §2.3 bulk seeding | **≥500 events in one deterministic pass** through the REAL ingestion endpoint `POST /api/event` (the exact path the tracking script uses) | `seed.py`, header-varied across virtual visitors/pages/referrers, all loopback |
| §2.3 readback | dashboard aggregate **equals what was sent**, after the async ClickHouse write flushes | authenticated dashboard JSON `GET /api/stats/<domain>/top-stats` |
| §2.2 mail round-trip | first-run **registration → 4-digit activation code email → sink → /activate → authenticated call succeeds** | `demo.py` PHASE 1, verification ENABLED |
| §2.2 absence | **event-anchored** absence pair: 0 mail to a control address (census-wide) + no residual to the registered user (per-address), anchored on the activation-COMPLETED event | `harness/mailsink.py` `checkpoint → assert_none_new` |
| F2 clock note | image libc, where scheduled jobs run, native clock-shaped messaging | `demo.py` PHASE 4 (orientation, no proof) |

Serves [`validation/FIXTURES.md`](../../validation/FIXTURES.md) §2.2 (msg-channel
census) and §2.3 (bulk content). Plausible is the first **two-datastore** bench
host: accounts/sites/settings live in Postgres, the event stream in ClickHouse —
so the leg additionally exercises Plausible's own hosting-kit ClickHouse tuning.

## Ports (loopback-only)

| Service | Host port | Container | Notes |
|---|---|---|---|
| Plausible app | `127.0.0.1:8085` | 8000 | HTTP + `/api/event` + dashboard |
| Mailpit UI / API | `127.0.0.1:8034` | 8025 | `harness/mailsink.py` talks here |
| Mailpit SMTP | `127.0.0.1:1034` | 1025 | Plausible sends here |
| Postgres | — internal only — | 5432 | NEVER host-published (host runs live PG on 5432) |
| ClickHouse | — internal only — | 8123/9000 | NEVER host-published |

Plausible is an Elixir/BEAM app: **EPMD / distribution ports (4369, dynamic) are
deliberately NOT published** — all BEAM networking stays inside the compose
network (4369 is occupied by the host's own erlang anyway).

## Images (digest-pinned)

| Image | Size | Digest | Source |
|---|---|---|---|
| `ghcr.io/plausible/community-edition:v3.2.1` | 167 MB | `sha256:33e60bfb…b62985` | NEW pull |
| `clickhouse/clickhouse-server:24.12-alpine` | 560 MB | `sha256:cd450891…f62621` | NEW pull (the heavy one) |
| `postgres:16-alpine` | 294 MB | `sha256:57c72fd2…c07777` | NEW pull (see deviation D3) |
| `axllent/mailpit:v1.30.4` | 34 MB | `sha256:5a49a77c…82d4f6` | REUSED (resident) |

Total NEW-pull footprint ≈ **1.0 GiB** (df 6.6 → 5.6 GiB across the three pulls),
inside the ≤1.8 GB budget. Versions track Plausible's own `community-edition`
v3.2.1 compose (ClickHouse `24.12-alpine`, Postgres `16-alpine`).

## Run

```bash
./setup.sh              # generate .env (0600) + durable dirs + verify images
./demo.sh               # up --wait -> seed -> proof -> down (durable data survives)
./demo.sh --keep        # ... but leave the stack running (app on :8085, sink :8034)
./demo.sh --reset       # wipe Postgres + ClickHouse + state first, then run (cold)
```

Health is gated on compose healthchecks and the `/api/health` poll inside the
Python — **never a sleep-as-sync**. Teardown is always scoped
(`docker compose -p noshit-f1-plausible down`); never a global prune. Durable
state (Postgres + ClickHouse) is bind-mounted under
`/home/user/fixture-runtime/plausible/` and survives teardown.

**Reset path:** `rm -rf /home/user/fixture-runtime/plausible/*` (or `./demo.sh
--reset`) — wipes the DBs + the `seed-state.json` founder credentials so the next
boot re-runs Plausible's fresh-DB init and the first-user registration.

**Timings (observed):** cold `--reset` ≈ 73 s; warm ≈ 35 s. The **first-ever**
boot on a cold OS page cache can take several minutes (Postgres + ClickHouse
migrations + a full cache warm before the HTTP endpoint accepts connections);
subsequent boots are ~15–30 s. `--wait-timeout` is 600 s to cover the cold case.

## The two async-visibility caveats (what §2.3 cares about)

Plausible's ingestion is **doubly asynchronous**, and this leg makes both
observable and handles each the event-driven way (poll for the event, never a
fixed sleep):

1. **Site-cache ingestion readiness (~25–30 s).** A just-created site is served
   from an in-memory `sites_by_domain` cache that refreshes on an interval;
   `POST /api/event` for the new domain is **DROPPED** (`x-plausible-dropped: 1`)
   until the cache picks it up. `seed.py` polls with custom `cache_probe` events
   (which do not count as pageviews) until one is accepted, *then* fires the bulk
   pass. Observed cold: **~24 s**; warm (site already cached): **~0 s**.
2. **ClickHouse buffered-write visibility (~2–4 s).** `POST /api/event` always
   returns **HTTP 202** and buffers the write; the row appears in ClickHouse (and
   the dashboard) a few seconds later. `seed.py` / `demo.py` poll the dashboard
   pageview count until it **converges** to `baseline + sent`, and record the
   latency. Observed: pageviews `0 → 500` in **~4 s** cold, **~2–3 s** warm.

Both are exactly the "async-visibility" behavior the build plan flags: a naive
"send then immediately assert" would false-negative. The leg's assertions are
event-anchored (convergence / acceptance), not timer-anchored.

## Deviations & findings (full record)

- **D1 — Registration is a LiveView (websocket), not a classic POST.** On CE the
  register form (`live "/register"`) is a Phoenix LiveView whose `handle_event
  ("register", …)` **itself inserts the user + provisions the team**, then sets
  `trigger_submit` so the browser does a real `POST /login` to establish the
  session. A plain `POST /login` with the form fields therefore creates **no**
  user (verified: 0 rows after the POST; also `FirstLaunchPlug` 302s everything to
  `/register` until the first user exists). We drive the register LiveView over a
  **minimal stdlib Phoenix LV v2 websocket client** (`seed.py:_LiveViewSocket`)
  to fire the `register` event, then complete login + activation over classic
  HTTP. The **activation MAIL round-trip is fully real**: the controller `login/2`
  issues the 4-digit code (`EmailVerification.issue_code`), it lands in the sink
  (subject `"<code> is your Plausible email verification code"`), we extract it
  from the real body and `POST /activate` with `code=<code>`. Login, activation
  (`POST /activate`), and site creation are all classic controllers.
- **D2 — `/var/lib/plausible` is NOT bind-mounted (unlike upstream's named
  volume).** The image ships that dir **empty and `0777` root**, and the runtime
  user is **uid 999**. A docker *named* volume inherits the `0777` (writable by
  999) — but the platform forbids named volumes (volatile store), and a *bind*
  mount owned by uid 1000/`0775` is **un-writable by uid 999**, so `tzdata`'s
  `data_dir` bootstrap crashes with `:enoent` on first boot. Nothing durable
  lives there (accounts → Postgres, events → ClickHouse, both bind-mounted), so
  the mount is simply omitted; tzdata rebuilds from its **bundled** release each
  boot (no network). This is the one place the platform's "durable state under
  fixture-runtime, no named volumes" rule required diverging from Plausible's
  reference compose.
- **D3 — Postgres 16, not the resident pg15.** Plausible v3.x pins
  `postgres:16-alpine`; `postgres:15-alpine` was resident but superseded. Pulling
  a supported alpine Postgres is inside budget per the reuse-if-compatible clause
  (the alpine base layer is shared with pg15, so the incremental pull was small).
- **D4 — Readback via the ungated dashboard JSON, not the public Stats API.** The
  public Stats API (`POST /api/v2/query`, `GET /api/v1/stats/aggregate`) and its
  key-mint helper `Plausible.Auth.create_stats_api_key` are gated behind the
  **StatsAPI business feature**, which a trial-less CE team lacks
  (`StatsAPI.check_availability` raises). We read back via the **authenticated
  dashboard JSON** `GET /api/stats/<domain>/top-stats` (the endpoint the free
  dashboard itself uses — ungated), which the leg's spec explicitly permits. (A
  working key *can* be minted headlessly by inserting the `ApiKey` changeset
  directly — `key_hash = lowercase hex sha256(SECRET_KEY_BASE ‖ key)`, default
  scope `stats:read:*` — which bypasses the feature gate; the dashboard JSON is
  simpler and needs no key, so we use it.)
- **D5 — Healthcheck uses `127.0.0.1`, not `localhost`.** The app binds IPv4
  `0.0.0.0:8000` only; inside the container `localhost` resolves to the IPv6 `::1`
  loopback, where nothing listens (connection refused). The compose healthcheck
  and the Python `wait_healthy` both use `127.0.0.1` / the host port.
- **D6 — Postgres and ClickHouse run as host uid 1000.** So their bind-mounted
  data stays host-owned and the documented `rm -rf` reset needs no sudo (same
  pattern as the listmonk/twenty legs). The ClickHouse alpine entrypoint execs
  `clickhouse-server` directly when started non-root; `CLICKHOUSE_SKIP_USER_SETUP=1`
  keeps the default (no-password) user Plausible connects as.
- **D7 / D8 — the two async-visibility caveats** (site-cache readiness; ClickHouse
  buffered writes) — see the section above. Both handled by event-anchored polling.
- **D9 — `TOTP_VAULT_KEY` is optional** (Plausible derives it from
  `SECRET_KEY_BASE` if absent) but must be **base64 of exactly 32 bytes** if set;
  `setup.sh` generates it (`openssl rand -base64 32`) explicitly. `SECRET_KEY_BASE`
  is required, ≥32 bytes (`openssl rand -base64 48`).
- **D10 — Presence+absence pair uses the registration activation email.** Team
  invites exist (`Teams.Invitations.invite/4`) but carry `check_team_member_limit`
  gating on CE (like the Stats API), so per the spec's fallback the pair ships as:
  PRESENCE = the activation email (real), ABSENCE = 0 to a never-touched control
  address (census-wide) + no residual to the registered user after activation
  settles (per-address), **anchored on the activation-completed event**.
- **D11 — ClickHouse config = Plausible's own hosting kit.** The four read-only
  drop-ins under `clickhouse/` (low-log `logs.xml`, `ipv4-only.xml`, `<16GB-RAM`
  `low-resources.xml` + `default-profile-low-resources-overrides.xml`) are copied
  verbatim from `plausible/community-edition` v3.2.1, with the `nofile` ulimit
  upstream uses. Kept minimal; data + logs bind-mounted to the durable disk.

## F2 clock story (orientation, printed by `demo.py` PHASE 4 — no proof here)

- **Image libc:** Alpine 3.22 / **musl** (`/lib/libc.musl-x86_64.so.1`; Dockerfile
  `FROM alpine:3.22.2`). A direct musl `LD_PRELOAD` of a glibc-built libfaketime
  won't work → F2 rung-2 uses the **glibc-sidecar** libfaketime pattern (same as
  the twenty / documenso / mastodon legs).
- **Where scheduled work runs:** **Oban cron inside the BEAM**. On CE
  (`config_env() == :ce` ⇒ `is_selfhost`) only `base_cron` runs — enumerable and
  harness-triggerable via the release: `bin/plausible rpc
  'Plausible.Workers.<W>.new(%{}) |> Oban.insert()'` (enqueue) or `…perform(%Oban.Job{args: %{}})`
  (inline). `DISABLE_CRON=true` turns cron + queues off entirely (a clean rung-3 gate).
- **Native clock-shaped behaviors (F2 targets):** `ScheduleEmailReports`
  (`0 * * * *`) enqueues **weekly/monthly** traffic-report emails;
  `TrafficChangeNotifier` (`*/15`) fires **spike/drop** notifications;
  `SendSiteSetupEmails` + `SendCheckStatsEmails` drive the onboarding email drip.
  Those longitudinal report emails are exactly the kind of messaging the
  platform's virtual clock exists to **compress** (days → minutes).

## Files

```
compose.yaml     plausible CE + clickhouse + postgres + mailpit; internal net; loopback ports
clickhouse/      the 4 read-only CH config drop-ins (verbatim from CE v3.2.1 hosting kit)
setup.sh         generate .env secrets (0600) + durable dirs + verify/pull pinned images
seed.py          PlausibleClient (WS register + classic HTTP + /api/event + dashboard) + bulk seed
demo.py          the 4 proofs (registration round-trip, ingest readback, absence pair, clock note)
demo.sh          deterministic cold start (up --wait -> seed -> proof -> down); --keep / --reset
.env.example     committed template; real .env is generated + gitignored
TRANSCRIPT.md    captured real cold run (df gates, timeline, ingest wall-time, sink evidence)
```

Durable state (Postgres + ClickHouse) lives OUTSIDE the repo at
`/home/user/fixture-runtime/plausible/`. Nothing runtime is committed; `.env` and
`seed-state.json` (founder credentials) are 0600 and gitignored.
