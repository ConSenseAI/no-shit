#!/usr/bin/env bash
# noshit-f1-listmonk — deterministic cold-start demo.
#
#   ./demo.sh            up --wait -> seed -> proof -> down   (data survives)
#   ./demo.sh --keep     same, but leave the stack running afterwards
#   ./demo.sh --reset    wipe the durable DB first (rm -rf fixture-runtime), then run
#
# Health is gated on compose healthchecks (--wait) and the API poll inside the
# Python — never a sleep-as-sync. Cleanup is always scoped to the project
# (-p noshit-f1-listmonk); never a global prune. The bind-mounted Postgres data
# under /home/user/fixture-runtime/listmonk/ is durable and is NOT removed by
# teardown. Exits nonzero if the proof fails.
set -uo pipefail
cd "$(dirname "$0")"

PROJECT=noshit-f1-listmonk
RUNTIME_DIR="/home/user/fixture-runtime/listmonk"
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
    echo "[demo]   app:      http://localhost:9002/admin/  (creds in ./.env)"
    echo "[demo]   sink UI:  http://localhost:8029"
    echo "[demo]   teardown: sg docker -c \"docker compose -p $PROJECT down\""
  else
    echo
    echo "[demo] tearing down (scoped: $PROJECT down; durable data preserved) ..."
    DC "down --remove-orphans" || true
  fi
}
trap cleanup EXIT

START=$(date +%s)

echo "[demo] setup (secrets + durable dir + images) ..."
./setup.sh

# Export the generated secrets so the Python clients (seed.py / demo.py) can read
# the Super Admin credentials. Compose reads .env on its own for substitution;
# the shell does not, so source it here.
set -a
# shellcheck disable=SC1091
. ./.env
set +a

if [[ "$RESET" == "1" ]]; then
  echo "[demo] --reset: wiping durable DB at $RUNTIME_DIR ..."
  DC "down --remove-orphans" || true
  rm -rf "${RUNTIME_DIR:?}/"* 2>/dev/null || true
  mkdir -p "$RUNTIME_DIR/db"
fi

echo "[demo] cold start: clearing any prior containers (data preserved) ..."
DC "down --remove-orphans" || true

echo "[demo] starting stack (up -d --wait) ..."
if ! DC "up -d --wait --wait-timeout 300"; then
  echo "[demo] compose up failed; recent app logs:"
  DC "logs --tail=60 app" || true
  exit 1
fi
echo "[demo] stack healthy."

SEED_START=$(date +%s)
echo "[demo] seeding (idempotent) ..."
if python3 seed.py; then SEED_RC=0; else SEED_RC=$?; fi
SEED_END=$(date +%s)
if [[ "$SEED_RC" != "0" ]]; then
  echo "[demo] seed FAILED (rc=$SEED_RC)"; exit "$SEED_RC"
fi

echo "[demo] running E2 proof ..."
PROOF_START=$(date +%s)
if python3 demo.py; then RC=0; else RC=$?; fi
PROOF_END=$(date +%s)

END=$(date +%s)
echo
echo "[demo] --- timings ---------------------------------------------"
echo "[demo] seed  : $((SEED_END - SEED_START))s (subscriber registration wall-time is in seed output)"
echo "[demo] proof : $((PROOF_END - PROOF_START))s (demo.py)"
echo "[demo] total : $((END - START))s (incl. up/seed/proof/teardown)"
echo "[demo] demo.py exit code: $RC"
echo "[demo] reset path: rm -rf $RUNTIME_DIR/*   (or ./demo.sh --reset)"
exit "$RC"
