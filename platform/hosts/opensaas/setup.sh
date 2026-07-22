#!/usr/bin/env bash
# Fetch pinned Open SaaS source, verify prerequisites, and pre-flight Stripe.
set -euo pipefail
cd "$(dirname "$0")"

SOURCE_SHA=81239fc18501502c52c4e58c4c7192eb6ea085e0
SOURCE_DIR=.run/source
NODE_IMAGE='node:24.14.1-bookworm-slim@sha256:e484ae3f1e3c378021c967fd42254f343c302a9263e412280eac32bf5bca7008'
POSTGRES_IMAGE='postgres:16-alpine@sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777'
MAILPIT_IMAGE='axllent/mailpit:v1.21.8@sha256:81370195cd4a0eab9604d17c2617a7525b0486f9365555253b6c5376c6350f1a'
CLI_IMAGE='stripe/stripe-cli@sha256:73a0449969bcb4bfa5a53ecb6db82f1ff873189d9e433aff72fa4c8e747acf81'

mask() {
  python3 -c 'import re,sys; s=sys.stdin.read(); s=re.sub(r"\b(rk|sk|pk|whsec)_(?:(test|live)_)?[A-Za-z0-9*]+", lambda m: f"{m.group(1)}_{m.group(2)}_***" if m.group(2) else f"{m.group(1)}_***", s); print(re.sub(r"\bacct_[A-Za-z0-9*]+", "acct_***", s), end="")'
}

say() { printf '%s\n' "$*" | mask; }

say '== Open SaaS bench leg - setup =='
if [ ! -f .env ] || ! grep -qE '^STRIPE_API_KEY=(rk|sk)_test_' .env; then
  say 'FATAL: create mode-600 .env from .env.example with a test Stripe key'
  exit 1
fi
[ "$(stat -c %a .env)" = 600 ] || { say 'FATAL: .env must be mode 600'; exit 1; }
command -v curl >/dev/null || { say 'FATAL: curl missing'; exit 1; }
command -v python3 >/dev/null || { say 'FATAL: python3 missing'; exit 1; }
sg docker -c 'docker version' >/dev/null || { say 'FATAL: Docker unavailable via sg docker -c'; exit 1; }

available=$(df -B1 --output=avail /home/user | tail -1 | tr -d ' ')
minimum=$((3 * 1024 * 1024 * 1024))
if [ "$available" -lt "$minimum" ]; then
  say "FATAL: only $available bytes free; refusing setup before large fetches"
  exit 1
fi
say "[ok] disk pre-flight: $available bytes free"

mkdir -p .run
if [ ! -f "$SOURCE_DIR/.nvmrc" ]; then
  say "[..] fetching Open SaaS commit $SOURCE_SHA from GitHub codeload"
  rm -rf "$SOURCE_DIR"
  mkdir -p "$SOURCE_DIR"
  curl -fsSL "https://codeload.github.com/wasp-lang/open-saas/tar.gz/$SOURCE_SHA" \
    | tar -xz --strip-components=1 -C "$SOURCE_DIR"
fi
if ! grep -q 'wasp: { version: "\^0.24.0" }' "$SOURCE_DIR/template/app/main.wasp.ts"; then
  say 'FATAL: pinned template no longer declares Wasp ^0.24.0'
  exit 1
fi
python3 - "$SOURCE_DIR/template/app/src/server/emailSender.wasp.ts" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
if 'provider: "SMTP"' not in text:
    old = '''  // NOTE: "Dummy" provider is just for local development purposes.\n  //   Make sure to check the server logs for the email confirmation url (it will not be sent to an address)!\n  //   Once you are ready for production, switch to e.g. "SendGrid" or "Mailgun" providers. Check out https://docs.opensaas.sh/guides/email-sending/ .\n  provider: "Dummy",'''
    new = '''  // Bench override: exercise the real SMTP path against this leg's Mailpit.\n  provider: "SMTP",'''
    if old not in text:
        raise SystemExit('FATAL: email sender patch context drifted')
    path.write_text(text.replace(old, new))
PY
say "[ok] source pin $SOURCE_SHA; SMTP bench override applied"

for image in "$NODE_IMAGE" "$POSTGRES_IMAGE" "$MAILPIT_IMAGE" "$CLI_IMAGE"; do
  if sg docker -c "docker image inspect '$image'" >/dev/null 2>&1; then
    say "[ok] pinned image present: $image"
  else
    say "[..] pulling pinned image: $image"
    sg docker -c "docker pull '$image'" >/dev/null
  fi
done

say '[..] Stripe scope pre-flight'
python3 stripe_ctl.py doctor

say '[..] building lockfile-pinned Wasp 0.24.0 dev image'
# This host's buildx plugin predates Compose's minimum; the classic builder
# consumes the same digest-pinned Dockerfile without pulling extra tooling.
sg docker -c 'DOCKER_BUILDKIT=0 docker build -t noshit-f0-opensaas-app:81239fc .'

say '== setup complete =='
