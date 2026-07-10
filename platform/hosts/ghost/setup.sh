#!/usr/bin/env bash
# setup.sh — one-time prep for the No Shit F0 Ghost + Stripe leg.
# Verifies prerequisites, ensures pinned images are present, and probes the
# Stripe key's scopes. Idempotent. Never prints the key.
set -uo pipefail
cd "$(dirname "$0")"
PROJECT=noshit-f0-ghost

echo "== No Shit F0 — Ghost + Stripe leg — setup =="

# 1. .env with a test-mode key
if [ ! -f .env ]; then
  echo "FATAL: no .env. Create it from the template and add your rk_test_ key:"
  echo "    cp .env.example .env   # then edit STRIPE_SECRET_KEY"
  exit 1
fi
if ! grep -qE '^STRIPE_SECRET_KEY=(rk|sk)_test_' .env; then
  echo "FATAL: .env has no test-mode STRIPE_SECRET_KEY (must start rk_test_/sk_test_)"
  exit 1
fi
echo "[ok] .env present with a test-mode key"

# 2. python
if python3 -c "import requests" 2>/dev/null; then
  echo "[ok] python3 + requests"
else
  echo "[warn] python 'requests' not found — clients fall back to stdlib urllib"
fi

# 3. docker + pinned images
if ! sg docker -c "docker version" >/dev/null 2>&1; then
  echo "FATAL: docker not usable via 'sg docker -c'"; exit 1
fi
for img in \
  "ghost:5-alpine" \
  "axllent/mailpit:v1.21.8" ; do
  if sg docker -c "docker image inspect '$img'" >/dev/null 2>&1; then
    echo "[ok] image present: $img"
  else
    echo "[..] pulling $img"
    sg docker -c "docker pull '$img'" || { echo "FATAL: pull failed for $img"; exit 1; }
  fi
done

# 4. probe the Stripe key scopes (masked)
echo "[..] probing Stripe key scopes:"
python3 stripe-clockctl.py doctor || true

echo "== setup complete — run ./demo.sh =="
