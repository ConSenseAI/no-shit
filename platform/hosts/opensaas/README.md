# Open SaaS + Stripe test-clock bench leg (F1 task 74 leg 1)

A cold, self-cleaning bench proof for the MIT-licensed Open SaaS starter: React +
Node/Wasp + Prisma/PostgreSQL, its real SMTP email path, and its native Stripe
subscription webhook. Compose project **`noshit-f0-opensaas`**. Loopback ports:
app **2369**, Mailpit UI **8028** / SMTP **1028**. PostgreSQL is never
host-published.

## TL;DR - what was proven

| Step | Observation | Result |
|---|---|---|
| 1. Cold start | New project-scoped PostgreSQL volume, Prisma migration, app HTTP 200 on `127.0.0.1:2369` | **PASS** (1 assertion) |
| 2. Messaging | Real email/password signup, Open SaaS SMTP provider, verification email in this leg's Mailpit, extracted token accepted | **PASS** (5 assertions) |
| 3. Account truth | Direct `psql` query finds exactly the signed-up `User`; no public state endpoint | **PASS** (2 assertions) |
| 4. Billing coupling | Real Stripe product/price/customer/subscription; member-customer mapping bootstrapped as Checkout would; Stripe CLI forwards signed events; PostgreSQL flips to `active`/`hobby` | **PASS** (4 assertions) |
| 5. Test clock | 8-day trial converts with one paid $12 invoice; next monthly boundary posts the second $12 invoice; app remains coherent | **PASS** (4 assertions) |
| 6. Cleanup | Test-clock deletion cascades customer/subscription; tool-owned prices/products archived; compose `down -v`; fleet lock released | **PASS** (orchestrator assertions) |

**16/16 application assertions passed.** Final cold demo wall-clock: **171 s**
(setup/build is separate). The verbatim masked run is in [`TRANSCRIPT.md`](TRANSCRIPT.md).

**Honest bottom line:** the browserless proof establishes the real signup, SMTP,
PostgreSQL, Stripe subscription, signed-webhook, conversion, and renewal paths.
It does **not** claim hosted-Checkout card entry: Stripe exposes no faithful API
for completing its hosted card UI browserlessly. The proof starts immediately
after that UI boundary by creating the same customer, member mapping, price
mapping, card, and subscription that Checkout would establish.

## Run it

```bash
cp ../ghost/.env .env
chmod 600 .env
# Rename STRIPE_SECRET_KEY= to STRIPE_API_KEY=; no publishable key is needed.
./setup.sh
./demo.sh
./demo.sh --keep
```

`setup.sh` is idempotent. It checks the disk floor, fetches the source pin, applies
the one-line SMTP bench override, checks all image pins, runs the masked Stripe
scope doctor, and builds the app image. `demo.sh` serializes live Stripe work with
`/home/user/chat/no-shit-fixtures/.stripe-lock`, then performs clean up -> create
plan mappings -> obtain a signing secret in shell memory -> compose up -> Stripe
CLI forwarding -> `prove.py` -> Stripe cleanup -> compose `down -v`. Any failed
assertion exits nonzero. `--keep` retains the stack but still deletes the proof's
clock-cascaded Stripe customer/subscription.

## Pins and observed versions

- Open SaaS tag `wasp-v0.24-template`, commit **`81239fc18501502c52c4e58c4c7192eb6ea085e0`** (tagged 2026-06-11), MIT.
- Wasp CLI **0.24.0**, exact npm dependency locked in `toolchain-package-lock.json`.
- Node **24.14.1**, linux/amd64 manifest digest `sha256:e484ae3f...ca7008` (index digest `sha256:b506e732...da26c`).
- PostgreSQL **16.14**, `postgres:16-alpine@sha256:57c72fd2...07777`.
- Mailpit **1.21.8**, `axllent/mailpit:v1.21.8@sha256:81370195...50f1a`.
- Stripe CLI **1.43.8**, `stripe/stripe-cli@sha256:73a04499...acf81`.
- Open SaaS pins Prisma **5.19.1** and Stripe Node SDK **18.1.0**; the app pins Stripe API `2025-04-30.basil`.

## Build strategy and network fetches

The preferred `wasp build` production route was investigated but not used. The
host had 6.07 GiB free and the leg's hard new-footprint ceiling was 2.5 GiB;
Wasp production output duplicates the generated server/client dependency tree
and requires a second runtime image. The documented **dev-mode fallback** was
therefore selected before exceeding budget. It is disclosed, not presented as
production parity.

The fallback still uses a digest-pinned container and real Open SaaS code. During
`setup.sh`, Docker fetches the Node base layers if absent; npm installs the exact
Wasp CLI lock and resolves Open SaaS's generated dependencies inside the image.
The Open SaaS template itself does not ship an app lockfile, so app dependencies
are constrained by its pinned/ranged `package.json` rather than a missing upstream
lock; this is a determinism gotcha for fixture builders. At runtime there are no
network package fetches: dependencies are prebuilt into the app image.

Fetch origins:

- Template tarball: GitHub codeload at the exact commit SHA.
- Wasp CLI and app npm dependencies: npm registry during image build only.
- Pinned OCI layers: Docker Hub during setup only.
- Stripe API/CLI: live sandbox during proof only.

## Deviations and gotchas

1. **Dev-mode fallback:** `wasp start`, not emitted production server/client. The
   fallback was selected to stay inside the 2.5 GiB ceiling. Cold migration,
   server, client, SMTP, PostgreSQL, Stripe SDK, and webhook code are all real.
2. **SMTP is a deliberate one-line bench override.** Upstream defaults to the
   dev-only `Dummy` sender; the fetched source is changed to `provider: "SMTP"`
   so evidence comes from Mailpit, never server-log scraping.
3. **Open SaaS merges every optional feature's environment schema.** Dummy values
   are required for unused Lemon Squeezy, Polar, OpenAI, S3, and analytics fields
   even though those features are not exercised. Stripe plan IDs and the webhook
   secret are real and injected only at runtime.
4. **New Stripe API shape:** under `2025-04-30.basil`, the subscription period end
   is on its item, not always top-level. The harness accepts the item field while
   preserving the exact renewal-boundary assertion.
5. **Unhandled Stripe events are noisy but acknowledged.** Open SaaS deliberately
   handles only `invoice.paid`, `customer.subscription.updated`, and
   `customer.subscription.deleted`; development logs the other forwarded events
   and returns 204.
6. **Classic Docker builder:** the host's buildx plugin is older than Compose's
   requirement. `setup.sh` uses `DOCKER_BUILDKIT=0 docker build` with the same
   digest-pinned Dockerfile rather than pulling new build tooling.
7. **Stripe scopes:** the restricted key needs products, prices, customers,
   payment methods, subscriptions, invoices, events, test clocks, and Stripe CLI
   session scope. `setup.sh` pre-flights the readable resource families; mutation
   failures remain hard proof failures.
8. **Clock discipline:** every advance polls to `ready` before and after mutation.
   All positions are explicit Unix datetimes; no bare date/midnight ambiguity.

## Image sizes and disk

- Open SaaS app image: **1,397,873,846 B (1.30 GiB)**, image ID `sha256:cc3f38b...095f6`.
- Node base: **223,983,405 B (214 MiB)**; shared by the app image.
- PostgreSQL: **294,211,945 B (281 MiB)**, already local before this leg.
- Mailpit: **29,645,272 B (28.3 MiB)**, already local.
- Stripe CLI: **45,556,736 B (43.4 MiB)**, already local.
- Gitignored fetched source/build metadata: **87 MiB**.
- Measured `/home` delta from first pre-pull reading to final teardown: about
  **98 MiB** net because most app layers reuse the Node base; conservative
  standalone leg assets are **~1.39 GiB**, below the 2.5 GiB ceiling. Final free
  disk: **6,513,393,664 B**.

## Key handling

The test key lives only in gitignored `.env`, mode 600. It is never printed,
logged, committed, or copied into generated reports. The app necessarily receives
the sandbox key in its runtime environment because Open SaaS's native Stripe SDK
uses it; Compose interpolation is transient and the value is not persisted in an
image, volume, transcript, or tracked file. `mask()` in every output
path redacts `rk_`/`sk_`/`pk_`/`whsec_` and account IDs, including exception text.
The Stripe CLI reads `.env` via Docker `--env-file`; the webhook signing secret
exists only in shell memory and runtime container environment. The proof's
Stripe identifiers are non-secret but omitted from the transcript except for the
self-cleaning test-clock ID. Live phases always acquire and release the fleet
lock.

## Files

| File | Role |
|---|---|
| `docker-compose.yml` | Loopback app/Mailpit + internal PostgreSQL, project-scoped volume, digest pins |
| `Dockerfile` | Node/Wasp 0.24 dev image with preinstalled generated dependencies |
| `setup.sh` | Fetch pin, SMTP override, disk/image/key checks, build |
| `prove.py` | 16-assertion acceptance proof with out-of-band `psql` truth |
| `stripe_ctl.py` | Masked Stripe API, doctor, ready polling, cleanup |
| `demo.sh` | Fleet-locked deterministic orchestration and completion log |
| `.env.example` / `.gitignore` | Secret discipline |
| `TRANSCRIPT.md` | Verbatim successful masked cold run |
