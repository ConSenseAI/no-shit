#!/usr/bin/env bash
# noshit-f0-documenso — deterministic cold-start demo.
#
#   ./demo.sh          cold start (down -v) -> up --build --wait -> proof -> down -v
#   ./demo.sh --keep   same, but leave the stack running afterwards
#
# Cleanup is always scoped to the project (-p noshit-f0-documenso). Never a
# global prune. Exits nonzero if the proof fails.
set -euo pipefail
cd "$(dirname "$0")"

KEEP=""
[[ "${1:-}" == "--keep" ]] && KEEP=1

DC="docker compose -p noshit-f0-documenso"
run() { sg docker -c "$*"; }

cleanup() {
  if [[ -z "$KEEP" ]]; then
    echo
    echo "[demo] tearing down (scoped: $DC down -v) ..."
    run "$DC down -v --remove-orphans" || true
  else
    echo
    echo "[demo] --keep set: stack left running."
    echo "[demo]   app:      http://localhost:3600"
    echo "[demo]   sink UI:  http://localhost:8026"
    echo "[demo]   teardown: sg docker -c \"$DC down -v\""
  fi
}
trap cleanup EXIT

START=$(date +%s)

echo "[demo] generating local secrets + signing cert (setup.sh) ..."
./setup.sh

echo "[demo] cold start: clearing any prior stack state ..."
run "$DC down -v --remove-orphans" || true

# The host's buildx predates the version `compose build` requires, so build the
# tiny sidecar image with the classic builder and let compose consume the tag.
echo "[demo] building fake-time sidecar image (classic builder) ..."
run "DOCKER_BUILDKIT=0 docker build -t noshit-f0-documenso-scheduler:local ./sidecar"

echo "[demo] starting stack (up --wait) ..."
run "$DC up -d --wait --wait-timeout 360"

echo "[demo] stack healthy. Running proof ..."
if python3 demo.py; then RC=0; else RC=$?; fi

END=$(date +%s)
echo
echo "[demo] demo.py exit code: $RC"
echo "[demo] total wall-clock duration: $((END - START))s"
exit "$RC"
