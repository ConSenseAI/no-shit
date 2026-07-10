# noshit-f0-killbill — engine-native clock leg

The Kill Bill leg of the F0 fixture-platform proof. It converts FIXTURES §2.1
**rung 1** (engine-native clock) and the platform's **exit criterion 1** from a
documentation claim into working fact:

> A subscription with an 8-day trial created at virtual **T0** converts,
> invoices, and **charges** when the Kill Bill **test clock — not wall time —**
> passes **T0+8d**; a subsequent cancellation is honored at the period boundary.
> The whole cycle runs in **minutes**.

One `./demo.sh` run does exactly that against a real `killbill/killbill` stack in
test mode, prints a virtual-time timeline, and tears down. Latest cold-start
runs: **73s** (core) / **105s** (with the email/sink stretch). See
[`TRANSCRIPT.md`](TRANSCRIPT.md).

Code is Apache-2.0 (repo `LICENSE-CODE`). Nothing here is sealed-corpus material.

---

## Quickstart

```bash
cd platform/hosts/killbill
./setup.sh                 # writes .env (gitignored) with a random tenant secret
./demo.sh                  # cold start -> full proof -> timeline -> tear down
./demo.sh --keep           # ... but leave the stack running afterwards
./demo.sh --with-email     # + install email-notifications plugin, assert mail in the sink
```

`./demo.sh` exits non-zero on any failed assertion. Docker is invoked as
`sg docker -c "docker ..."` throughout (group-session quirk on this host);
`demo.py` handles that internally.

Requirements: Docker + Compose v2/v5, Python 3 (stdlib only). `--with-email`
additionally needs host internet the first time (to fetch the plugin JAR, then
cached in `data/`).

**Manual clock poking** (stack must be up, e.g. after `--keep`):

```bash
python3 clockctl.py get                       # {"currentUtcTime": ..., "localDate": ...}
python3 clockctl.py set 2026-01-23T12:00:00   # move to an absolute instant
python3 clockctl.py advance 8                  # advance N days (PUT ?days=N)
python3 clockctl.py queues 10                  # block until notification queues drain
```

---

## What's in the stack

`docker-compose.yml` (project **`noshit-f0-killbill`**), three services on one
**internal** bridge network:

| Service | Image | Host port (loopback only) | Notes |
|---|---|---|---|
| `killbill` | `killbill/killbill:0.24.16` | `127.0.0.1:8080` → 8080 | `KILLBILL_SERVER_TEST_MODE=true` → `/1.0/kb/test/clock` |
| `db` | `killbill/mariadb:0.24` | **none** | schema pre-loaded; **never** host-published |
| `mailpit` | `axllent/mailpit:v1.21.8` | `127.0.0.1:8025` / `127.0.0.1:1025` | sink UI / SMTP (FIXTURES §2.2) |

Ports match the platform registry (killbill 8080, mailpit 8025/1025). The
database is deliberately never published — the host runs its own Postgres on
5432 and a live service on 4000, both untouched. All published ports bind
`127.0.0.1`. Cleanup is always scoped:

```bash
sg docker -c "docker compose -p noshit-f0-killbill down -v"
```

## Files

| File | Purpose |
|---|---|
| `docker-compose.yml` | the three-service stack; test mode + SMTP→mailpit wiring |
| `.env.example` / `setup.sh` | config template / generator (real `.env` is gitignored) |
| `catalog.xml` | minimal catalog: `Standard` product, `standard-monthly` plan (8-day $0 trial → $29.95/mo evergreen) |
| `clockctl.py` | stdlib client for the test clock; library **and** CLI |
| `demo.py` / `demo.sh` | the deterministic end-to-end proof (`demo.sh` execs `demo.py`) |
| `install-email-plugin.sh` | optional stretch: install email-notifications into a running stack |
| `TRANSCRIPT.md` | verbatim captured runs |
| `data/` | host-cached plugin JAR+DDL (gitignored); created by the stretch path |

The demo also reuses the shared sink client `../../harness/mailsink.py`.

## Image sizes

Pulled prebuilt (no source builds):

| Image | Size |
|---|---|
| `killbill/killbill:0.24.16` | 1.36 GB |
| `killbill/mariadb:0.24` | 339 MB |
| `axllent/mailpit:v1.21.8` | 29.6 MB |
| email-notifications plugin JAR (host-cached in `data/`, stretch only) | 24 MB |

A running stack adds a ~190 MB `dbdata` volume (removed by `down -v`).
`docker system df` at hand-off reported 6.73 GB of images total — most of that
is unrelated to this leg (a sibling Ghost leg and pre-existing images share the
daemon); this leg's own pull footprint is the ~1.73 GB of the three images above.

---

## Deviations from FIXTURES §2.1 assumptions (found at F0)

These are the reasons the demo is written the way it is; feed back into
`validation/FIXTURES.md` at its next bump.

1. **Date-vs-datetime is real — bare dates land *before* the event** (the trap
   FIXTURES §9 flags). The subscription starts a few seconds past `T0`'s
   time-of-day, so the trial→paid `PHASE` event is scheduled at, e.g.,
   `2026-01-23T08:00:01`. Moving the clock with the **bare date**
   `requestedDate=2026-01-23` (a `LocalDate`, interpreted at `00:00:00`) is still
   inside the trial and **nothing converts** — verified directly (midnight set →
   only the $0 trial invoice; noon set → the $29.95 conversion appears).
   **Mitigation:** every boundary is crossed with an explicit **noon** datetime,
   and the target instant is read from the subscription's own `PHASE` /
   `billingEndDate` events rather than assumed. `clockctl` promotes any bare date
   it is handed to noon for the same reason.

2. **The test clock keeps ticking in real time once positioned.** After a `set`
   to `…T08:00:00`, objects created seconds later carry `…T08:00:0x` and events
   inherit that skew. A time script that assumes a frozen instant will drift by
   seconds; the ~4-hour noon margin absorbs it. (This is the "timestamp skew"
   risk in §2.1, observed in-engine rather than across a webhook.)

3. **The account `/invoices` list endpoint does not compute totals** — it returns
   `amount`/`balance` as `0.0` for every row on 0.24.16. The same invoice fetched
   by id (`GET /1.0/kb/invoices/{id}?withItems=true`) correctly shows the
   `RECURRING $29.95` item. Invoice assertions must read per-invoice, which
   `demo.py` does.

4. **Settlement is asynchronous — poll the observable, don't read once.** After a
   clock move, invoice-item creation and auto-payment complete on background
   queues; a single immediate read can catch a shell invoice. `demo.py` drains
   `/1.0/kb/test/queues` and polls for the settled state (RECURRING item present,
   `PURCHASE`/`SUCCESS`), never a fixed sleep.

5. **The DB password is effectively pinned to `killbill`.** The image's
   `killbill.sh` hardcodes `-pkillbill` in its DB-readiness probe, so
   `KB_DB_PASSWORD` can't be changed without breaking startup. Fine here (DB is
   internal-only), but noted so it isn't "hardened" into a boot failure.

6. **Env-var config forms.** `KILLBILL_SERVER_TEST_MODE=true` works (the image's
   `setenv2.sh` aliases it to `org.killbill.server.test.mode`) — the build-plan
   assumption holds. But **mail** properties have no such alias, so they must be
   given in canonical `KB_org_killbill_mail_smtp_*` form; plain `KILLBILL_MAIL_*`
   is silently dropped. The compose file uses the canonical form.

### Stretch (email-notifications plugin → sink coupling)

Attempted and **working** (`./demo.sh --with-email`), but with real friction —
worth recording since the other F0 leg (documenso) formally carries the
sink-coupling exit criterion:

- **The killbill container has no internet egress** on the internal network, so
  in-container `kpm install` cannot fetch the plugin. Worked around by
  downloading the JAR on the host and running KPM offline against a copied file:
  `kpm install_java_plugin email-notifications --from-source-file=… --version=0.8.2`.
- The plugin needs its **DDL** (`email_notifications_configuration`) loaded and a
  **Kill Bill restart** to load the OSGI bundle. (DB client is `mariadb`, not
  `mysql` — MariaDB 11.)
- **SMTP comes from the core `org.killbill.mail.smtp.*` properties**, already
  wired to `mailpit:1025` in the compose file — *not* the plugin-prefixed ones.
  The per-tenant `uploadPluginConfig` only needs to supply
  `defaultEvents=INVOICE_CREATION,INVOICE_PAYMENT_SUCCESS,SUBSCRIPTION_CANCEL`.
- **Emails render only for accounts that carry a `locale`.** Without it the
  plugin throws `Translation for locale [null] isn't found` and sends nothing —
  events fire, SMTP is reachable, but zero mail. `demo.py` sets `locale=en_US`.
  This was the single most time-consuming non-obvious gotcha.
- Version pin: KB 0.24 → email-notifications **0.8.2** (killbill-cloud
  `plugins_directory.yml`).

Because the plugin lives in the container's writable layer (not the image), it
does **not** survive `down -v`; `--with-email` reinstalls it after each cold
start. That is why plugin install is a script invoked by the demo rather than an
image change — and why the core proof (the non-negotiable part) carries no plugin
dependency at all.
