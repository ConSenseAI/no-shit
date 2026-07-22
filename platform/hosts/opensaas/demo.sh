#!/usr/bin/env bash
# Deterministic Open SaaS bench orchestrator: clean -> up -> prove -> cleanup -> down.
set -uo pipefail
cd "$(dirname "$0")"
PROJECT=noshit-f0-opensaas
CLI_IMAGE='stripe/stripe-cli@sha256:73a0449969bcb4bfa5a53ecb6db82f1ff873189d9e433aff72fa4c8e747acf81'
LOCK=/home/user/chat/no-shit-fixtures/.stripe-lock
PROGRESS=/home/user/chat/no-shit-fixtures/briefs/G1-progress.log
KEEP=0
[ "${1:-}" = --keep ] && KEEP=1

mask() {
  python3 -c 'import re,sys; s=sys.stdin.read(); s=re.sub(r"\b(rk|sk|pk|whsec)_(?:(test|live)_)?[A-Za-z0-9*]+", lambda m: f"{m.group(1)}_{m.group(2)}_***" if m.group(2) else f"{m.group(1)}_***", s); print(re.sub(r"\bacct_[A-Za-z0-9*]+", "acct_***", s), end="")'
}
say() { printf '%s\n' "$*" | mask; }
read_key() {
  python3 - <<'PY'
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if line.startswith('STRIPE_API_KEY='):
        print(line.split('=', 1)[1].strip().strip('"').strip("'"), end='')
        break
PY
}
dc() {
  STRIPE_API_KEY="$SECRET_KEY" \
  STRIPE_WEBHOOK_SECRET="$WEBHOOK_SECRET" \
  PAYMENTS_HOBBY_SUBSCRIPTION_PLAN_ID="$PRICE_ID" \
  PAYMENTS_PRO_SUBSCRIPTION_PLAN_ID="$PRICE_ID" \
  PAYMENTS_CREDITS_10_PLAN_ID="$CREDITS_PRICE_ID" \
  sg docker -c "docker compose -p '$PROJECT' $*"
}

if [ ! -f .env ] || [ "$(stat -c %a .env 2>/dev/null)" != 600 ]; then
  say 'FATAL: .env missing or not mode 600; run ./setup.sh'
  exit 2
fi
if ! mkdir "$LOCK" 2>/dev/null; then
  say 'FATAL: live Stripe fleet lock is busy'
  exit 2
fi
LOCK_HELD=1
SECRET_KEY=$(read_key)
WEBHOOK_SECRET=''
PRODUCT_ID=''
PRICE_ID=''
CREDITS_PRICE_ID=''
PROOF_COMPLETE=0

cleanup() {
  sg docker -c "docker rm -f noshit-f0-opensaas-stripe-listener" >/dev/null 2>&1 || true
  python3 stripe_ctl.py cleanup >/dev/null 2>&1 || true
  if [ "$KEEP" = 0 ] && [ -n "$WEBHOOK_SECRET" ] && [ -n "$PRICE_ID" ]; then
    dc down -v >/dev/null 2>&1 || true
  fi
  if [ "${LOCK_HELD:-0}" = 1 ]; then
    rmdir "$LOCK" 2>/dev/null || true
    LOCK_HELD=0
  fi
}
trap cleanup EXIT INT TERM

wall_start=$(date +%s)
say "== Open SaaS cold proof ($PROJECT) =="
df -h /home/user | mask

# Nothing from prior runs survives: DB and dependency volumes are project-scoped.
STRIPE_WEBHOOK_SECRET=whsec_placeholder \
PAYMENTS_HOBBY_SUBSCRIPTION_PLAN_ID=price_placeholder \
PAYMENTS_PRO_SUBSCRIPTION_PLAN_ID=price_placeholder \
PAYMENTS_CREDITS_10_PLAN_ID=price_placeholder \
STRIPE_API_KEY="$SECRET_KEY" \
sg docker -c "docker compose -p '$PROJECT' down -v" >/dev/null 2>&1 || true
python3 stripe_ctl.py cleanup || exit 1

say '[1/6] create real Stripe plan mappings'
runtime=$(STRIPE_API_KEY="$SECRET_KEY" python3 - <<'PY'
import json, time
from stripe_ctl import Stripe, load_key
s = Stripe(load_key())
run = str(int(time.time()))
p = s.post('/products', {'name': f'Open SaaS Bench {run}', 'metadata': {'tool': 'noshit-f0-opensaas', 'run': run}})
monthly = s.post('/prices', {'product': p['id'], 'unit_amount': 1200, 'currency': 'usd', 'recurring': {'interval': 'month'}, 'metadata': {'tool': 'noshit-f0-opensaas', 'run': run}})
credits = s.post('/prices', {'product': p['id'], 'unit_amount': 500, 'currency': 'usd', 'metadata': {'tool': 'noshit-f0-opensaas', 'run': run}})
print(json.dumps({'product_id': p['id'], 'price_id': monthly['id'], 'credits_price_id': credits['id']}))
PY
) || exit 1
mkdir -p .run
printf '%s\n' "$runtime" > .run/runtime.json
PRODUCT_ID=$(python3 -c 'import json; print(json.load(open(".run/runtime.json"))["product_id"])')
PRICE_ID=$(python3 -c 'import json; print(json.load(open(".run/runtime.json"))["price_id"])')
CREDITS_PRICE_ID=$(python3 -c 'import json; print(json.load(open(".run/runtime.json"))["credits_price_id"])')
say '  [ok] product + recurring/one-time prices created (IDs intentionally not printed)'

say '[2/6] obtain Stripe CLI signing secret in shell memory'
WEBHOOK_SECRET=$(sg docker -c "docker run --rm --env-file "$PWD/.env" '$CLI_IMAGE' listen --print-secret" 2>/dev/null) || exit 1
if [[ "$WEBHOOK_SECRET" != whsec_* ]]; then
  say 'FATAL: Stripe CLI did not return a signing secret'
  exit 1
fi
say '  [ok] webhook signing secret received and masked'

say '[3/6] cold compose up (PostgreSQL migration + real Open SaaS dev server)'
if ! dc up -d --wait; then
  say 'FATAL: compose did not become healthy; masked app logs follow'
  dc logs --tail=100 app 2>&1 | mask
  exit 1
fi

say '[4/6] start real Stripe CLI webhook forwarding'
network="${PROJECT}_opensaas"
sg docker -c "docker rm -f noshit-f0-opensaas-stripe-listener" >/dev/null 2>&1 || true
sg docker -c "docker run -d --rm --name noshit-f0-opensaas-stripe-listener --network '$network' --env-file "$PWD/.env" '$CLI_IMAGE' listen --forward-to http://app:2369/payments-webhook" >/dev/null || exit 1

say '[5/6] prove signup -> SMTP -> psql -> webhook -> renewal'
if ! STRIPE_API_KEY="$SECRET_KEY" python3 prove.py; then
  say 'FATAL: proof assertion failed'
  dc logs --tail=100 app 2>&1 | mask
  exit 1
fi
PROOF_COMPLETE=1

say '[6/6] cleanup tool-owned Stripe resources and stack'
python3 stripe_ctl.py cleanup || exit 1
sg docker -c "docker rm -f noshit-f0-opensaas-stripe-listener" >/dev/null 2>&1 || true
if [ "$KEEP" = 1 ]; then
  say '--keep: stack remains at app :2369, Mailpit :8028 / SMTP :1028'
else
  dc down -v || exit 1
fi
wall=$(( $(date +%s) - wall_start ))
printf '%s task74-leg1 OpenSaaS bench proof complete; assertions=16/16; wall=%ss\n' "$(date -u +%FT%TZ)" "$wall" >> "$PROGRESS"
say "== proof complete: 16/16; cold wall ${wall}s =="
exit 0
