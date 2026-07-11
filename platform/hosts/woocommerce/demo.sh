#!/usr/bin/env bash
# noshit-f1-woocommerce — deterministic cold-start demo.
#
#   ./demo.sh            up --wait -> install -> seed -> proof -> down  (data survives)
#   ./demo.sh --keep     same, but leave the stack running afterwards
#   ./demo.sh --reset    wipe the durable runtime first, then run from scratch
#
# Health gating: compose healthchecks (`up --wait`) + a host-side HTTP poll on
# 127.0.0.1:8083 — events, never sleeps-as-sync. Teardown is always scoped to
# the project (-p noshit-f1-woocommerce); never a global prune. The bind-mounted
# state under /home/user/fixture-runtime/woocommerce/ is durable and is NOT
# removed by teardown.
#
# RESET PATH (documented): the mariadb/wordpress entrypoints chown db/ and
# html/ contents to in-container uids (mysql, www-data), so a plain
# `rm -rf /home/user/fixture-runtime/woocommerce/*` from the login user hits
# permission errors. `./demo.sh --reset` performs the equivalent wipe
# container-assisted (alpine, scoped to that one bind mount) and then cold-starts.
set -uo pipefail
cd "$(dirname "$0")"

PROJECT=noshit-f1-woocommerce
RUNTIME_DIR="/home/user/fixture-runtime/woocommerce"
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
    echo "[demo]   store:    http://127.0.0.1:8083  (admin creds in ./.env — not printed)"
    echo "[demo]   sink UI:  http://127.0.0.1:8028"
    echo "[demo]   teardown: sg docker -c \"docker compose -p $PROJECT down\""
  else
    echo
    echo "[demo] tearing down (scoped: $PROJECT down; durable data preserved) ..."
    DC "down --remove-orphans" || true
  fi
}
trap cleanup EXIT

T_START=$(date +%s)

if [[ "$RESET" == "1" ]]; then
  echo "[demo] --reset: wiping durable runtime (container-assisted; see header) ..."
  DC "down --remove-orphans" || true
  sg docker -c "docker run --rm -v $RUNTIME_DIR:/wipe alpine:latest sh -c 'rm -rf /wipe/db /wipe/html'" \
    || { echo "[demo] FAIL: reset wipe"; exit 1; }
fi

echo "[demo] setup: secrets + durable dirs ..."
./setup.sh || { echo "[demo] FAIL: setup.sh"; exit 1; }
T_SETUP=$(date +%s)

echo "[demo] starting stack (up -d --wait; healthchecks gate readiness) ..."
DC "up -d --wait --wait-timeout 420" || { echo "[demo] FAIL: compose up"; exit 1; }
T_UP=$(date +%s)

echo "[demo] polling app over the published loopback port (event-gated, no blind sleeps) ..."
ok=0
for _ in $(seq 1 120); do
  if curl -fsS -o /dev/null "http://127.0.0.1:8083/"; then ok=1; break; fi
  sleep 1
done
[[ "$ok" == "1" ]] || { echo "[demo] FAIL: app never answered on 127.0.0.1:8083"; exit 1; }
echo "[demo] app answering on 127.0.0.1:8083"

echo "[demo] install (idempotent: core + WooCommerce + store config) ..."
./install.sh || { echo "[demo] FAIL: install.sh"; exit 1; }
T_INSTALL=$(date +%s)

echo "[demo] seeding proof (one pass, wall-time recorded) ..."
./seed.sh || { echo "[demo] FAIL: seed.sh"; exit 1; }
T_SEED=$(date +%s)

echo "[demo] running E2 proof (demo.py) ..."
if python3 demo.py; then RC=0; else RC=$?; fi
T_DEMO=$(date +%s)

echo
echo "[demo] ---- step timeline (wall seconds) ----"
echo "[demo]   setup    : $((T_SETUP - T_START))s"
echo "[demo]   up+health: $((T_UP - T_SETUP))s"
echo "[demo]   install  : $((T_INSTALL - T_UP))s"
echo "[demo]   seed     : $((T_SEED - T_INSTALL))s"
echo "[demo]   proof    : $((T_DEMO - T_SEED))s"
echo "[demo]   total    : $((T_DEMO - T_START))s"
echo "[demo] demo.py exit code: $RC"
exit "$RC"
