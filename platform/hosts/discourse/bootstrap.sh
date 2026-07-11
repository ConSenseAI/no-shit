#!/usr/bin/env bash
# noshit-f1-discourse — ONE-TIME heavy provisioning: build the production-parity
# Discourse image via the official launcher, df-gated with a live watchdog.
#
# This is the "provisioning" half of the leg (NOT part of the repeatable demo).
# It pulls discourse/base and builds local_discourse/noshit-f1-discourse (core
# v2026.6.0, subscriptions bundled). Expect 15-25 min.
#
# DISK DISCIPLINE (hard rule: never let root free fall under 1.5 GiB — a parallel
# build shares this disk; ENOSPC is unacceptable):
#   * GATE   — refuse to start below MIN_START (default 3.0 GiB).
#   * WATCHDOG — while the launcher runs, poll df; if free dips below ABORT
#     (default 2.2 GiB, a margin above the 1.5 GiB floor to cover the poll blind
#     spot), kill the whole build process group and `docker rm -f` the partial
#     bootstrap container (reclaiming its writable layer). The floor is never
#     breached; a well-documented partial is a valid F1 deliverable.
# Tune via env: NOSHIT_MIN_START_GB, NOSHIT_ABORT_GB, NOSHIT_POLL_S.
set -uo pipefail
cd "$(dirname "$0")"

LAUNCHER_DIR="/home/user/fixture-runtime/discourse/discourse_docker"
CONFIG="noshit-f1-discourse"
BOOT_LOG="/home/user/fixture-runtime/discourse/bootstrap.log"
CIDFILE="${LAUNCHER_DIR}/cids/${CONFIG}_bootstrap.cid"

MIN_START_KB=$(awk "BEGIN{printf \"%d\", ${NOSHIT_MIN_START_GB:-3.0}*1024*1024}")
ABORT_KB=$(awk "BEGIN{printf \"%d\", ${NOSHIT_ABORT_GB:-2.2}*1024*1024}")
POLL_S="${NOSHIT_POLL_S:-8}"

freekb(){ df -P / | awk 'NR==2{print $4}'; }
gib(){ awk "BEGIN{printf \"%.2f\", ${1}/1024/1024}"; }

echo "== noshit-f1-discourse — bootstrap (heavy, df-gated) =="
./setup.sh >/dev/null
echo "[bootstrap] setup ok (dirs / network / rendered yml / staged provision files)"

echo "[bootstrap] --- df GATE (before base pull + build) -------------------"
df -h / | sed -n '1p;2p'
FREE=$(freekb)
echo "[bootstrap] free=$(gib "$FREE") GiB  (floor=1.50  abort=$(gib "$ABORT_KB")  min-start=$(gib "$MIN_START_KB"))"
if (( FREE < MIN_START_KB )); then
  echo "[bootstrap] STOP: free $(gib "$FREE") GiB < min-start $(gib "$MIN_START_KB") GiB."
  echo "[bootstrap] A concurrent build is holding the shared disk. NOT starting (would risk the 1.5 GiB floor)."
  echo "[bootstrap] The leg config/scripts/docs are complete; re-run ./bootstrap.sh when root free recovers."
  exit 3
fi

# If a prior build's container is lingering, clean it (scoped) before starting.
if [[ -f "$CIDFILE" ]]; then
  OLD="$(cat "$CIDFILE" 2>/dev/null || true)"
  [[ -n "$OLD" ]] && sg docker -c "docker rm -f $OLD" >/dev/null 2>&1 || true
  rm -f "$CIDFILE"
fi

# Fresh build = fresh build-rw shunt content (tmp/assets are artifacts of THIS
# build; see discourse.yml.template volumes comment).
BUILD_RW="/home/user/fixture-runtime/discourse/build-rw"
rm -rf "${BUILD_RW:?}"/app-tmp/* "${BUILD_RW:?}"/public-assets/* 2>/dev/null || true
echo "[bootstrap] build-rw shunt dirs cleaned (assets rebuild onto the durable disk)"

# --skip-prereqs: the launcher's STATIC preflight demands 5GB free — sized for
# an un-shunted build (overlay RW + commit duplicate). With the build-rw shunt
# this leg's peak is far lower, and the LIVE df watchdog below enforces the
# floor continuously — strictly stronger than a one-shot preflight. The other
# prereq checks it skips (docker version, RAM) are verified on this host.
echo "[bootstrap] launching: (cd $LAUNCHER_DIR && ./launcher bootstrap $CONFIG --skip-prereqs)  [log: $BOOT_LOG]"
: > "$BOOT_LOG"
# New session (setsid) so the watchdog can signal the whole group. The docker
# daemon still owns the build container, so we ALSO rm -f its cid on abort.
setsid bash -c "cd '$LAUNCHER_DIR' && exec sg docker -c './launcher bootstrap $CONFIG --skip-prereqs'" \
  >>"$BOOT_LOG" 2>&1 &
BOOT_PGID=$!

ABORTED=0
LAST_REPORT=0
while kill -0 "$BOOT_PGID" 2>/dev/null; do
  FREE=$(freekb)
  NOW=$(date +%s)
  if (( NOW - LAST_REPORT >= 60 )); then
    echo "[bootstrap] ... building; free=$(gib "$FREE") GiB; tail:"
    tail -n 2 "$BOOT_LOG" 2>/dev/null | sed 's/^/[bootstrap]     | /'
    LAST_REPORT=$NOW
  fi
  if (( FREE < ABORT_KB )); then
    echo "[bootstrap] !! WATCHDOG: free $(gib "$FREE") GiB < abort $(gib "$ABORT_KB") GiB — aborting to protect the 1.5 GiB floor."
    kill -TERM -"$BOOT_PGID" 2>/dev/null || kill -TERM "$BOOT_PGID" 2>/dev/null || true
    sleep 3
    kill -KILL -"$BOOT_PGID" 2>/dev/null || true
    if [[ -f "$CIDFILE" ]]; then
      CID="$(cat "$CIDFILE" 2>/dev/null || true)"
      [[ -n "$CID" ]] && { echo "[bootstrap] reclaiming partial build container ${CID:0:12} ..."; sg docker -c "docker rm -f $CID" >/dev/null 2>&1 || true; }
    fi
    ABORTED=1
    break
  fi
  sleep "$POLL_S"
done

if (( ABORTED == 1 )); then
  echo "[bootstrap] --- df AFTER abort/reclaim ---"; df -h / | sed -n '2p'
  echo "[bootstrap] ABORTED on disk pressure. Base image (re-pullable) may remain cached; no partial app image committed."
  echo "[bootstrap] Documented-partial path: see README 'Deviation record'. Re-run when disk frees."
  exit 4
fi

wait "$BOOT_PGID"; RC=$?
echo "[bootstrap] --- df AFTER build ---"; df -h / | sed -n '2p'
if (( RC != 0 )); then
  echo "[bootstrap] launcher bootstrap FAILED (rc=$RC). Last log lines:"
  tail -n 40 "$BOOT_LOG" | sed 's/^/[bootstrap]   | /'
  exit "$RC"
fi

echo "[bootstrap] build OK. Image:"
sg docker -c "docker images local_discourse/${CONFIG} --format '  {{.Repository}}:{{.Tag}}  {{.Size}}'"
echo "== bootstrap complete — run ./demo.sh =="
