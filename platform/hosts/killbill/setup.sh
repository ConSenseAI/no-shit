#!/usr/bin/env bash
# Generate .env (gitignored) from .env.example with a fresh random tenant secret.
# Idempotent: refuses to clobber an existing .env. No real secrets are involved
# — this only fills KB_TENANT_API_SECRET for the throwaway demo tenant.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .env ]; then
  echo ".env already exists; leaving it untouched."
  exit 0
fi

# 24 url-safe chars from the kernel CSPRNG.
SECRET="$(head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 24)"
sed "s|^KB_TENANT_API_SECRET=.*|KB_TENANT_API_SECRET=${SECRET}|" .env.example > .env
echo "Wrote .env (KB_TENANT_API_SECRET randomized)."
