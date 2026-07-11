#!/usr/bin/env bash
# noshit-f1-mastodon — deterministic cold-start demo (the nli★ gold standard).
#
#   ./demo.sh            up (staged) -> provision -> seed -> proof -> down  (data survives)
#   ./demo.sh --keep     same, but leave the stack running afterwards
#   ./demo.sh --reset    wipe the durable DB/redis/media first (cold start), then run
#
# STAGED bring-up (Mastodon /health needs a migrated DB, so schema is loaded
# out-of-band BEFORE web starts): setup -> up db/redis/mailpit --wait -> schema
# (schema:load+seed on a fresh DB, else migrate) -> up web/sidekiq --wait ->
# provision (open registration + owner admin + minted OAuth token) -> seed.py ->
# demo.py. Health is gated on compose healthchecks (--wait) + the API /health
# poll — never a sleep-as-sync. Cleanup is always scoped (-p noshit-f1-mastodon);
# never a global prune. Durable bind-mounts under /home/user/fixture-runtime/
# mastodon/ survive teardown. Exits nonzero if the proof fails.
#
# PROVISIONING vs DEMO (honest split):
#   * Provisioning (this script, before the proof): schema load, `Setting.
#     registrations_mode=open`, the Owner admin (tootctl accounts create --role
#     Owner), and a minted OAuth admin token (rails runner Doorkeeper). Idempotent.
#   * Demo (seed.py + demo.py): the bulk seed + the five proofs. Must re-run green.
set -uo pipefail
cd "$(dirname "$0")"

PROJECT=noshit-f1-mastodon
RUNTIME_DIR="/home/user/fixture-runtime/mastodon"
MASTODON_IMAGE="ghcr.io/mastodon/mastodon:v4.6.2@sha256:c5a92a6ec505086060a5a1fdec3be286da7f3cbd06e5158359e7f720e14b912c"
KEEP=0; RESET=0
for a in "$@"; do
  case "$a" in
    --keep) KEEP=1 ;;
    --reset) RESET=1 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown flag: $a"; exit 2 ;;
  esac
done

DC() { sg docker -c "docker compose -p $PROJECT $*"; }
DE() { sg docker -c "docker compose -p $PROJECT exec -T $*"; }
df_free_gib() { df -BG --output=avail / | tail -1 | tr -dc '0-9'; }

cleanup() {
  if [[ "$KEEP" == "1" ]]; then
    echo
    echo "[demo] --keep set: stack left running."
    echo "[demo]   web:      http://localhost:3002/   (loopback; creds/token in ./.env)"
    echo "[demo]   sink UI:  http://127.0.0.1:8032"
    echo "[demo]   teardown: sg docker -c \"docker compose -p $PROJECT down\""
  else
    echo
    echo "[demo] tearing down (scoped: $PROJECT down; durable data preserved) ..."
    DC "down --remove-orphans" || true
  fi
}
trap cleanup EXIT

START=$(date +%s)
echo "[demo] df at start:"; df -h / | sed -n '2p'

echo "[demo] setup (secrets + durable dirs + df-gated images) ..."
./setup.sh

# Export generated secrets so the Python clients read them (compose reads .env on
# its own; the shell does not).
set -a
# shellcheck disable=SC1091
. ./.env
set +a

if [[ "$RESET" == "1" ]]; then
  echo "[demo] --reset: wiping durable DB/redis/media at $RUNTIME_DIR (media dir is uid-991 -> container-assisted) ..."
  DC "down --remove-orphans" || true
  sg docker -c "docker run --rm --user 0 -v ${RUNTIME_DIR}:/rt --entrypoint sh ${MASTODON_IMAGE} -c 'rm -rf /rt/db /rt/redis /rt/system'" || true
  ./setup.sh >/dev/null   # recreate {db,redis,system,captures} + re-chown media to 991
fi

echo "[demo] cold start: clearing any prior containers (data preserved) ..."
DC "down --remove-orphans" || true

# df gate before the DB setup (rule 7 floor 1.5 GiB)
FREE="$(df_free_gib)"
echo "[demo] df gate before db setup: ${FREE} GiB free (floor 1.5)"
if [[ "$FREE" -lt 2 ]]; then echo "[demo] FATAL: <2 GiB free before db setup; stopping cleanly."; exit 1; fi

echo "[demo] up infra (db, redis, mailpit) --wait ..."
if ! DC "up -d db redis mailpit --wait --wait-timeout 120"; then
  echo "[demo] infra failed to become healthy:"; DC "ps"; exit 1
fi

# --- schema: schema:load+seed on a fresh DB, migrate on a warm one ----------
# NB: the SQL has spaces, so it must be passed as one properly-quoted arg (the
# $*-based DE helper would split it); escape the inner quotes through `sg`.
SCHEMA="$(sg docker -c "docker compose -p $PROJECT exec -T db psql -U mastodon -d mastodon_production -tAc \"SELECT to_regclass('public.accounts')\"" 2>/dev/null | tr -d ' ')"
if [[ -z "$SCHEMA" ]]; then
  echo "[demo] fresh DB -> rails db:schema:load db:seed ..."
  DC "run --rm -T web bin/rails db:schema:load db:seed" || { echo "[demo] schema load failed"; exit 1; }
else
  echo "[demo] existing schema -> rails db:migrate (idempotent) ..."
  DC "run --rm -T web bin/rails db:migrate" || { echo "[demo] migrate failed"; exit 1; }
fi

echo "[demo] up app (web, sidekiq) --wait ..."
if ! DC "up -d web sidekiq --wait --wait-timeout 180"; then
  echo "[demo] app failed to become healthy; recent web logs:"; DC "logs --tail=40 web"; exit 1
fi
echo "[demo] stack healthy."

# --- provisioning (idempotent): open registration, owner admin, OAuth token --
echo "[demo] provision: open registration ..."
DE web bin/rails runner /provision/site_settings.rb >/dev/null

echo "[demo] provision: ensure Owner admin (tootctl accounts create --role Owner) ..."
OWNER_OUT="$(DE web bin/tootctl accounts create "$MASTO_OWNER_USERNAME" --email "$MASTO_OWNER_EMAIL" --confirmed --role Owner 2>&1 || true)"
if grep -qi 'New password:' <<<"$OWNER_OUT"; then
  OWNER_PW="$(grep -i 'New password:' <<<"$OWNER_OUT" | awk '{print $NF}')"
  { grep -v '^MASTO_OWNER_PASSWORD=' .env 2>/dev/null || true; printf 'MASTO_OWNER_PASSWORD=%s\n' "$OWNER_PW"; } > .env.tmp && mv .env.tmp .env && chmod 600 .env
  echo "[demo]   owner created (password captured into .env, redacted)"
else
  echo "[demo]   owner already present (idempotent)"
fi

echo "[demo] provision: mint owner OAuth admin token (rails runner Doorkeeper) ..."
KEY="$(DE web bin/rails runner /provision/mint_token.rb "$MASTO_OWNER_USERNAME" 'read+write+admin:read+admin:write' 2>/dev/null | sed -n 's/^NOSHIT_TOKEN=//p' | tr -d '\r\n ')"
if [[ -z "$KEY" ]]; then echo "[demo] FATAL: could not mint owner admin token"; exit 1; fi
{ grep -v '^MASTO_ADMIN_TOKEN=' .env 2>/dev/null || true; printf 'MASTO_ADMIN_TOKEN=%s\n' "$KEY"; } > .env.tmp && mv .env.tmp .env && chmod 600 .env
export MASTO_ADMIN_TOKEN="$KEY"
echo "[demo]   admin token minted into ./.env (0600) [redacted]"

# --- seed (bulk content) ----------------------------------------------------
SEED_START=$(date +%s)
echo "[demo] seeding (idempotent) ..."
if ! python3 seed.py; then echo "[demo] seed FAILED"; exit 1; fi
SEED_END=$(date +%s)

# --- the E2 proof -----------------------------------------------------------
echo "[demo] running E2 proof (demo.py) ..."
PROOF_START=$(date +%s)
if python3 demo.py; then RC=0; else RC=$?; fi
PROOF_END=$(date +%s)

END=$(date +%s)
echo
echo "[demo] --- timings ---------------------------------------------"
echo "[demo] seed  : $((SEED_END - SEED_START))s (status wall-time is inside seed output)"
echo "[demo] proof : $((PROOF_END - PROOF_START))s (demo.py)"
echo "[demo] total : $((END - START))s (incl. up/schema/provision/seed/proof/teardown)"
echo "[demo] df at end:"; df -h / | sed -n '2p'
echo "[demo] reset path: ./demo.sh --reset  (wipe db/redis/media, cold start ~schema load 1-2 min)"
echo "[demo] demo.py exit code: $RC"
exit "$RC"
