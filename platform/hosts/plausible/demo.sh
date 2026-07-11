#!/usr/bin/env bash
# noshit-f1-plausible — deterministic cold-start demo.
#
#   ./demo.sh            up --wait -> seed -> proof -> down   (durable data survives)
#   ./demo.sh --keep     same, but leave the stack running afterwards
#   ./demo.sh --reset    wipe the durable DB + ClickHouse + state first, then run
#
# Health is gated on compose healthchecks (--wait) and the /api/health poll inside
# the Python — never a sleep-as-sync. Cleanup is always scoped to the project
# (-p noshit-f1-plausible); never a global prune. The bind-mounted Postgres +
# ClickHouse data under /home/user/fixture-runtime/plausible/ are durable and are
# NOT removed by teardown. Exits nonzero if the proof fails.
#
# NB Plausible's FIRST boot runs Postgres + ClickHouse migrations AND a full cache
# warm before its HTTP endpoint accepts connections — this can take several minutes
# on a slow shared disk. The --wait-timeout is generous; warm boots are fast.
set -uo pipefail
cd "$(dirname "$0")"

PROJECT=noshit-f1-plausible
RUNTIME_DIR="/home/user/fixture-runtime/plausible"
KEEP=0
RESET=0
for a in "$@"; do
  case "$a" in
    --keep) KEEP=1 ;;
    --reset) RESET=1 ;;
    *) echo "unknown flag: $a"; exit 2 ;;
  esac
done

DC() { sg docker -c "docker compose -p $PROJECT $*"; }

cleanup() {
  if [[ "$KEEP" == "1" ]]; then
    echo
    echo "[demo] --keep set: stack left running."
    echo "[demo]   app:      http://localhost:8085/   (founder creds in $RUNTIME_DIR/seed-state.json, 0600)"
    echo "[demo]   sink UI:  http://localhost:8034"
    echo "[demo]   teardown: sg docker -c \"docker compose -p $PROJECT down\""
  else
    echo
    echo "[demo] tearing down (scoped: $PROJECT down; durable data preserved) ..."
    DC "down --remove-orphans" || true
  fi
}
trap cleanup EXIT

START=$(date +%s)

echo "[demo] setup (secrets + durable dirs + images) ..."
./setup.sh

# Export the generated secrets so compose substitution can read them. Compose
# reads .env on its own; the shell does not, so source it here.
set -a
# shellcheck disable=SC1091
. ./.env
set +a

if [[ "$RESET" == "1" ]]; then
  echo "[demo] --reset: wiping durable data at $RUNTIME_DIR ..."
  DC "down --remove-orphans" || true
  # Wipe Postgres data, ClickHouse data/logs, and the founder state file so the
  # next boot re-runs Plausible's fresh-DB init + the first-user registration.
  rm -rf "${RUNTIME_DIR:?}/"* 2>/dev/null || true
  mkdir -p "$RUNTIME_DIR/db" "$RUNTIME_DIR/clickhouse/data" "$RUNTIME_DIR/clickhouse/logs" "$RUNTIME_DIR/captures"
fi

echo "[demo] cold start: clearing any prior containers (data preserved) ..."
DC "down --remove-orphans" || true

echo "[demo] starting stack (up -d --wait; first boot migrates PG + CH + warms caches, be patient) ..."
if ! DC "up -d --wait --wait-timeout 600"; then
  echo "[demo] compose up failed / not healthy in time; recent plausible logs:"
  DC "logs --tail=80 plausible" || true
  echo "[demo] recent clickhouse logs:"
  DC "logs --tail=20 clickhouse" || true
  exit 1
fi
echo "[demo] stack healthy."

SEED_START=$(date +%s)
echo "[demo] seeding (bootstrap founder + site + >=500 events, idempotent) ..."
if python3 seed.py; then SEED_RC=0; else SEED_RC=$?; fi
SEED_END=$(date +%s)
if [[ "$SEED_RC" != "0" ]]; then
  echo "[demo] seed FAILED (rc=$SEED_RC)"; exit "$SEED_RC"
fi

echo "[demo] running E2 + messaging proof ..."
PROOF_START=$(date +%s)
if python3 demo.py; then RC=0; else RC=$?; fi
PROOF_END=$(date +%s)

END=$(date +%s)
echo
echo "[demo] --- timings ---------------------------------------------"
echo "[demo] seed  : $((SEED_END - SEED_START))s (event-send wall-time is in seed output)"
echo "[demo] proof : $((PROOF_END - PROOF_START))s (demo.py)"
echo "[demo] total : $((END - START))s (incl. up/seed/proof/teardown)"
echo "[demo] demo.py exit code: $RC"
echo "[demo] reset path: rm -rf $RUNTIME_DIR/*   (or ./demo.sh --reset)"
exit "$RC"
