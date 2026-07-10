#!/usr/bin/env bash
# demo.sh — deterministic F0 proof for the Ghost + Stripe test-clock leg.
#
#   up  ->  prove  ->  virtual-time timeline  ->  Stripe cleanup  ->  down
#
# Proves (see README for floor-vs-target):
#   * Stripe test-clock cycle (floor): frozen T0, forward-only advances through
#     the 8-day-trial time script, poll-to-ready, delete-cascade. With a
#     subscription-scoped key it auto-upgrades to the full trial->convert->cancel
#     lifecycle; with the F0 test-clock-only key it proves the clock mechanics.
#   * Ghost membership + mail sink (target): member signup -> transactional mail
#     captured in this leg's Mailpit -> member state in Ghost.
#
# Flags:  --keep   leave the stack running (Ghost :2368, Mailpit :8027)
# Exit:   nonzero on any failed assertion or infra failure.
set -uo pipefail
cd "$(dirname "$0")"
PROJECT=noshit-f0-ghost
KEEP=0
[ "${1:-}" = "--keep" ] && KEEP=1

DC() { sg docker -c "docker compose -p $PROJECT $*"; }
banner() { echo; echo "======================================================================"; echo "  $*"; echo "======================================================================"; }

wall_start=$(date +%s)
rc=0
mkdir -p .run

# --- preflight -------------------------------------------------------------
if ! grep -qE '^STRIPE_SECRET_KEY=(rk|sk)_test_' .env 2>/dev/null; then
  echo "FATAL: .env missing a test-mode STRIPE_SECRET_KEY. Run ./setup.sh first."
  exit 2
fi

# --- 1. UP -----------------------------------------------------------------
banner "1. UP  (docker compose, project $PROJECT)"
if ! DC "up -d --wait"; then
  echo "compose up failed; recent ghost logs:"; DC "logs --tail=40 ghost" || true
  DC "down -v" || true
  exit 1
fi

# --- 2. Stripe test-clock proof (FLOOR) ------------------------------------
banner "2. PROVE — Stripe sandbox test-clock cycle (floor)"
if ! python3 stripe-clockctl.py full-cycle --json-log .run/stripe.json; then
  echo "!! Stripe clock proof FAILED"; rc=1
fi

# --- 3. Ghost membership + mail sink proof (TARGET) ------------------------
banner "3. PROVE — Ghost membership + mail-sink (target)"
if ! python3 ghost_prove.py; then
  echo "!! Ghost membership/mail proof FAILED"; rc=1
fi

# --- 4. Stripe cleanup (self-cleaning) -------------------------------------
banner "4. Stripe cleanup — delete any tool-owned test clocks"
python3 stripe-clockctl.py cleanup || true

# --- 5. DOWN / keep --------------------------------------------------------
if [ "$KEEP" = "1" ]; then
  banner "--keep: stack left running"
  echo "  Ghost admin : http://localhost:2368/ghost/"
  echo "  Mailpit UI  : http://localhost:8027/"
  echo "  Teardown    : sg docker -c \"docker compose -p $PROJECT down -v\""
else
  banner "5. DOWN  (scoped teardown: down -v on $PROJECT only)"
  DC "down -v"
fi

wall=$(( $(date +%s) - wall_start ))
banner "DEMO COMPLETE — wall ${wall}s — exit $rc"
[ "$rc" = "0" ] && echo "  All attainable assertions PASSED." \
                 || echo "  One or more assertions FAILED (see above)."
exit $rc
