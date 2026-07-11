#!/usr/bin/env bash
# noshit-f1-woocommerce — SEEDING PROOF wrapper (FIXTURES §2.3 bulk content).
#
# ONE command seeds >=120 products across >=3 categories in a single pass:
# a single `wp eval-file` inside the wpcli container (one WP boot, one PHP
# process — not 120 separate CLI invocations). This script records the
# wall-time, which is the number the proof reports.
#
# Idempotent: re-runs skip existing SKUs (see seed/seed-products.php).
set -uo pipefail
cd "$(dirname "$0")"
PROJECT=noshit-f1-woocommerce

echo "[seed] one-pass bulk seeding: wp eval-file /seed/seed-products.php"
T0=$(date +%s.%N)
sg docker -c "docker compose -p $PROJECT run --rm -T wpcli wp eval-file /seed/seed-products.php" \
  | sed 's/^/[seed]   /'
RC=${PIPESTATUS[0]}
T1=$(date +%s.%N)
WALL=$(python3 -c "print(f'{${T1}-${T0}:.1f}')")

if [[ "$RC" -ne 0 ]]; then
  echo "[seed] FAIL (rc=$RC) after ${WALL}s"
  exit "$RC"
fi
echo "[seed] SEEDING WALL-TIME: ${WALL}s (one command, incl. container spawn + WP boot)"
