#!/usr/bin/env bash
# noshit-f1-discourse — deterministic demo orchestration.
#
#   ./demo.sh            start stack -> provision -> proof -> stop  (data survives)
#   ./demo.sh --keep     same, but leave the stack running afterwards
#   ./demo.sh --reset    destroy container + wipe durable /shared, re-init, then run
#
# PROVISIONING vs REPEATABLE (documented honestly):
#   * ONE-TIME provisioning = ./bootstrap.sh  (df-gated launcher BUILD of the
#     production-parity image; 15-25 min). demo.sh invokes it only if the image
#     is missing. It is NOT part of the repeatable path.
#   * REPEATABLE demo = everything here: launcher/docker START of the built
#     container + mailpit, an idempotent admin+API-key provision (rails runner,
#     one cold start), then demo.py (signup round-trip + absence + seed + plugin),
#     then STOP. This part must re-run green.
#
# Cleanup is always scoped (launcher stop/destroy of THIS config; mailpit compose
# -p noshit-f1-discourse). Never a global prune. The bind-mounted state under
# /home/user/fixture-runtime/discourse survives stop (only --reset wipes it).
set -uo pipefail
cd "$(dirname "$0")"

PROJECT="noshit-f1-discourse"
CONTAINER="noshit-f1-discourse"
RUNTIME_DIR="/home/user/fixture-runtime/discourse"
LAUNCHER_DIR="${RUNTIME_DIR}/discourse_docker"
SHARED="${RUNTIME_DIR}/shared/standalone"
IMAGE="local_discourse/${CONTAINER}"

KEEP=0; RESET=0
for a in "$@"; do
  case "$a" in
    --keep) KEEP=1 ;;
    --reset) RESET=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown flag: $a"; exit 2 ;;
  esac
done

DC() { sg docker -c "docker compose -p $PROJECT -f mailpit.compose.yaml $*"; }
# --skip-prereqs: the launcher's static 5GB preflight is sized for un-shunted
# builds; this leg's build-rw shunt + bootstrap.sh's live df watchdog cover the
# disk story (see README deviations). start/stop/destroy carry the flag too.
LAUNCH() { sg docker -c "cd '$LAUNCHER_DIR' && ./launcher $* --skip-prereqs"; }
D() { sg docker -c "docker $*"; }

cleanup() {
  if [[ "$KEEP" == "1" ]]; then
    echo
    echo "[demo] --keep set: stack left running."
    echo "[demo]   forum:    http://127.0.0.1:8084/   (admin creds/key in ./.env — key is secret)"
    echo "[demo]   sink UI:  http://127.0.0.1:8031"
    echo "[demo]   stop:     sg docker -c \"cd '$LAUNCHER_DIR' && ./launcher stop $CONTAINER\" ; ./demo.sh (re-run)"
  else
    echo
    echo "[demo] bringing stack DOWN (scoped) — durable /shared preserved ..."
    LAUNCH "stop $CONTAINER" >/dev/null 2>&1 || true
    DC "down --remove-orphans" >/dev/null 2>&1 || true
    echo "[demo] down: discourse container stopped (image + /shared kept for fast re-run); mailpit removed."
  fi
}
trap cleanup EXIT

START=$(date +%s)
echo "[demo] df at start:"; df -h / | sed -n '2p'

echo "[demo] setup (dirs / network / rendered yml / staged provision files) ..."
./setup.sh >/dev/null
echo "[demo] setup ok."

if [[ "$RESET" == "1" ]]; then
  echo "[demo] --reset: destroying container + wiping durable /shared (image kept) ..."
  LAUNCH "destroy $CONTAINER" >/dev/null 2>&1 || true
  DC "down --remove-orphans" >/dev/null 2>&1 || true
  rm -rf "${SHARED:?}/"* 2>/dev/null || true
  ./setup.sh >/dev/null   # recreate dirs + re-stage provision files after wipe
  echo "[demo] reset done (next start re-inits an empty DB: initdb + migrate, ~1-2 min)."
fi

# --- ONE-TIME image build (only if missing) ---------------------------------
if ! D "image inspect $IMAGE" >/dev/null 2>&1; then
  echo "[demo] built image $IMAGE not found — running one-time ./bootstrap.sh (df-gated, heavy) ..."
  if ! ./bootstrap.sh; then
    echo "[demo] bootstrap did not complete (see message above / bootstrap.log)."
    echo "[demo] Cannot run the proof without the image. This is the documented disk-resistance partial."
    exit 5
  fi
fi

# --- mailpit sink up --------------------------------------------------------
echo "[demo] starting mailpit sink (compose up -d --wait) ..."
DC "up -d --wait --wait-timeout 60" || { echo "[demo] mailpit failed to start"; DC "logs --tail=30 mailpit"; exit 1; }

# --- discourse container up (START, not build) ------------------------------
if D "ps --format '{{.Names}}'" | grep -qx "$CONTAINER"; then
  echo "[demo] discourse already running."
elif D "ps -a --format '{{.Names}}'" | grep -qx "$CONTAINER"; then
  echo "[demo] starting existing discourse container (docker start; preserves --network + ports) ..."
  D "start $CONTAINER" >/dev/null
else
  echo "[demo] first container run via launcher start ..."
  LAUNCH "start $CONTAINER"
fi

# --- wait for the app to serve (event, not a fixed sleep) -------------------
echo "[demo] waiting for app health (GET /srv/status) ..."
ok=0
for _ in $(seq 1 150); do
  if curl -sf -o /dev/null http://127.0.0.1:8084/srv/status 2>/dev/null; then ok=1; break; fi
  sleep 2
done
[[ "$ok" == "1" ]] || { echo "[demo] app did not become healthy in time"; LAUNCH "logs $CONTAINER" 2>/dev/null | tail -40 || true; exit 1; }
echo "[demo] app healthy."

# --- provision admin + API key (idempotent; secret-safe capture) ------------
echo "[demo] provisioning admin + API key (rails runner admin_seed.rb) ..."
if ! OUT="$(D "exec -u discourse -w /var/www/discourse $CONTAINER bash -lc 'bundle exec rails runner /shared/admin_seed.rb'" 2>&1)"; then
  echo "[demo] provisioning FAILED:"; printf '%s\n' "$OUT" | grep -v '^NOSHIT_APIKEY=' | tail -25; exit 1
fi
printf '%s\n' "$OUT" | grep -v '^NOSHIT_APIKEY=' | sed 's/^/[seed] /'
KEY="$(printf '%s\n' "$OUT" | sed -n 's/^NOSHIT_APIKEY=//p' | head -1)"
if [[ -z "$KEY" ]]; then echo "[demo] ERROR: no API key captured from provisioning"; exit 1; fi
# write DISCOURSE_API_KEY into the gitignored .env (0600), never echoed
{ grep -v '^DISCOURSE_API_KEY=' .env 2>/dev/null || true; printf 'DISCOURSE_API_KEY=%s\n' "$KEY"; } > .env.tmp
mv .env.tmp .env; chmod 600 .env
echo "[demo] admin API key captured into ./.env (0600) [redacted]"

# --- the repeatable proof ---------------------------------------------------
echo "[demo] running E2 proof (demo.py) ..."
PROOF_START=$(date +%s)
if python3 demo.py; then RC=0; else RC=$?; fi
PROOF_END=$(date +%s)

END=$(date +%s)
echo
echo "[demo] --- timings ---------------------------------------------"
echo "[demo] proof : $((PROOF_END - PROOF_START))s (demo.py — seed wall-time is inside its output)"
echo "[demo] total : $((END - START))s (incl. start/provision/proof/teardown)"
echo "[demo] df at end:"; df -h / | sed -n '2p'
echo "[demo] reset path: ./demo.sh --reset  (destroy+wipe /shared, re-init ~1-2 min; image kept)"
echo "[demo]             full rebuild: sg docker -c \"docker rmi $IMAGE\" then ./bootstrap.sh (~15-25 min)"
echo "[demo] demo.py exit code: $RC"
exit "$RC"
