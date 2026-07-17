#!/usr/bin/env bash
# Real Stripe events -> Stripe CLI -> Ghost lifecycle-coupling proof.
set -uo pipefail
cd "$(dirname "$0")"

PROJECT=noshit-f0-ghost
BASE=(-f docker-compose.yml -f docker-compose.coupling.yml)
CLI_IMAGE='stripe/stripe-cli@sha256:73a0449969bcb4bfa5a53ecb6db82f1ff873189d9e433aff72fa4c8e747acf81'

if ! grep -qE '^STRIPE_SECRET_KEY=(rk|sk)_test_' .env || ! grep -qE '^STRIPE_PUBLISHABLE_KEY=pk_test_' .env; then
  echo 'FATAL: .env requires non-empty test secret and publishable Stripe keys'
  exit 2
fi

read_env() {
  python3 - "$1" <<'PY'
import sys
from pathlib import Path
key = sys.argv[1] + '='
for line in Path('.env').read_text().splitlines():
    if line.startswith(key):
        print(line.split('=', 1)[1].strip().strip('"').strip("'"), end='')
        break
PY
}

SECRET_KEY=$(read_env STRIPE_SECRET_KEY)
PUBLISHABLE_KEY=$(read_env STRIPE_PUBLISHABLE_KEY)
WEBHOOK_SECRET=$(sg docker -c "docker run --rm -e STRIPE_API_KEY='$SECRET_KEY' '$CLI_IMAGE' listen --print-secret")
if [[ "$WEBHOOK_SECRET" != whsec_* ]]; then
  echo 'FATAL: Stripe CLI did not return a webhook signing secret'
  exit 2
fi

cleanup_variant() {
  sg docker -c "docker rm -f noshit-f0-ghost-stripe-listener" >/dev/null 2>&1 || true
  STRIPE_WEBHOOK_SECRET="$WEBHOOK_SECRET" sg docker -c "docker compose -p '$PROJECT' ${BASE[*]} --profile mysql down -v" >/dev/null 2>&1 || true
}

cleanup() {
  sg docker -c "docker rm -f noshit-f0-ghost-stripe-listener" >/dev/null 2>&1 || true
  STRIPE_WEBHOOK_SECRET="$WEBHOOK_SECRET" sg docker -c "docker compose -p '$PROJECT' ${BASE[*]} --profile mysql down -v" >/dev/null 2>&1 || true
  python3 stripe-clockctl.py cleanup >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

run_variant() {
  local variant=$1
  local profile_args=''
  local db_client='sqlite3'
  if [ "$variant" = mysql ]; then
    profile_args='--profile mysql'
    db_client='mysql'
  fi

  echo "== Ghost <-> Stripe lifecycle coupling: $variant =="
  STRIPE_WEBHOOK_SECRET="$WEBHOOK_SECRET" GHOST_DB="$db_client" \
    sg docker -c "docker compose -p '$PROJECT' ${BASE[*]} $profile_args up -d --wait"

  # Direct-key settings are seeded after Ghost creates its DB, then Ghost is
  # restarted so its settings cache configures Stripe with the same real key.
  STRIPE_SECRET_KEY="$SECRET_KEY" STRIPE_PUBLISHABLE_KEY="$PUBLISHABLE_KEY" \
    python3 seed_stripe_settings.py --db "$variant" || return 1
  STRIPE_WEBHOOK_SECRET="$WEBHOOK_SECRET" GHOST_DB="$db_client" \
    sg docker -c "docker compose -p '$PROJECT' ${BASE[*]} $profile_args restart ghost"

  sg docker -c "docker rm -f noshit-f0-ghost-stripe-listener" >/dev/null 2>&1 || true
  sg docker -c "docker run -d --rm --name noshit-f0-ghost-stripe-listener --network '${PROJECT}_f0ghost' -e STRIPE_API_KEY='$SECRET_KEY' '$CLI_IMAGE' listen --headers 'Host:localhost:2368,X-Forwarded-Proto:https' --forward-to http://ghost:2368/members/webhooks/stripe/" >/dev/null
  python3 coupling_prove.py --db "$variant" || return 1

  cleanup_variant
}

wall_start=$(date +%s)
run_variant sqlite || exit 1
run_variant mysql || exit 1
echo "== coupling proof complete: wall $(( $(date +%s) - wall_start ))s =="
