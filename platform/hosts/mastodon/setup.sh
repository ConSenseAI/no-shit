#!/usr/bin/env bash
# noshit-f1-mastodon — one-time local prep (DB-independent).
#
# Produces the gitignored .env the stack needs at boot, generating EVERY Mastodon
# secret with the image's OWN rake/rails tasks (never a hand-rolled substitute):
#   SECRET_KEY_BASE, OTP_SECRET   <- bundle exec rails secret         (x2)
#   VAPID_{PRIVATE,PUBLIC}_KEY    <- rake mastodon:webpush:generate_vapid_key
#   ACTIVE_RECORD_ENCRYPTION_*    <- rake db:encryption:init          (trio, v4.3+)
# plus a random POSTGRES_PASSWORD and MASTO_SEED_PASSWORD (openssl). Ensures the
# durable bind-mount dirs and chowns public/system to the image uid (991).
# Verifies the pinned images are present (df-gated pull only if missing; postgres/
# redis are small, mailpit is reused). Never prints a secret. The DB schema,
# owner admin, and OAuth token are provisioned by demo.sh once the stack is up
# (they need a running DB) — see README's provisioning-vs-demo split.
#
# Idempotent: keeps an existing .env unless run with --force.
set -euo pipefail
cd "$(dirname "$0")"
FORCE="${1:-}"

RUNTIME_DIR="/home/user/fixture-runtime/mastodon"
MASTODON_IMAGE="ghcr.io/mastodon/mastodon:v4.6.2@sha256:c5a92a6ec505086060a5a1fdec3be286da7f3cbd06e5158359e7f720e14b912c"
POSTGRES_IMAGE="postgres:15-alpine@sha256:3d0f7584ed7d04e27fa050d6683a74746608faf21f202be78460d679cc56461f"
REDIS_IMAGE="redis:7-alpine@sha256:6ab0b6e7381779332f97b8ca76193e45b0756f38d4c0dcda72dbb3c32061ab99"
MAILPIT_IMAGE="axllent/mailpit:v1.30.4@sha256:5a49a77c5bdbe7c5474450b4f46348d09949df3695257729c93a30369382d4f6"
MASTO_UID=991   # the image's own mastodon uid; public/system must be writable by it

echo "== noshit-f1-mastodon — setup =="

# --- docker usable? ---------------------------------------------------------
if ! sg docker -c "docker version" >/dev/null 2>&1; then
  echo "FATAL: docker not usable via 'sg docker -c'"; exit 1
fi

# --- durable bind-mount dirs ------------------------------------------------
mkdir -p "${RUNTIME_DIR}"/{db,redis,system,captures}
echo "[ok] durable dirs: ${RUNTIME_DIR}/{db,redis,system,captures}"

# --- df gate + image presence (pull only what's missing; df-gated) ----------
df_free_gib() { df -BG --output=avail / | tail -1 | tr -dc '0-9'; }
ensure_image() {  # $1=image  $2=approx-disk-note
  local img="$1"
  if sg docker -c "docker image inspect '$img'" >/dev/null 2>&1; then
    echo "[ok] image present (reused): ${img%@*}"
    return 0
  fi
  local free; free="$(df_free_gib)"
  echo "[df] before pull ${img%@*} ($2): ${free} GiB free"
  if [ "$free" -lt 3 ]; then
    echo "FATAL: df gate — <3 GiB free before pulling ${img%@*} (floor 1.5, budget guard). Stopping cleanly."
    exit 1
  fi
  echo "[..] pulling ${img%@*} ..."
  sg docker -c "docker pull '$img'" || { echo "FATAL: pull failed: ${img%@*}"; exit 1; }
  echo "[df] after pull: $(df_free_gib) GiB free"
}
ensure_image "$MAILPIT_IMAGE"  "reused ~34MB"
ensure_image "$REDIS_IMAGE"    "~39MB"
ensure_image "$POSTGRES_IMAGE" "~292MB"
ensure_image "$MASTODON_IMAGE" "~766MB"

# --- public/system must be writable by the image uid (991), not the host uid -
# (media attachments + account ARCHIVES are written here by web+sidekiq). Done
# via the image itself running as root — no extra image pulled.
sg docker -c "docker run --rm --user 0 -v ${RUNTIME_DIR}/system:/system --entrypoint chown ${MASTODON_IMAGE} -R ${MASTO_UID}:${MASTO_UID} /system" \
  && echo "[ok] chowned ${RUNTIME_DIR}/system to uid ${MASTO_UID} (image writes media+archives here)"

# --- .env (secrets) ---------------------------------------------------------
if [[ -f .env && "$FORCE" != "--force" ]]; then
  echo "[ok] .env exists — keeping it (pass --force to regenerate; also reset the DB then)"
  exit 0
fi

echo "[..] generating Mastodon secrets with the image's own tasks (4 rails/rake boots; ~30-45s) ..."
# ONE container; SECRET_KEY_BASE_DUMMY lets the tasks boot without a real secret.
# Output goes into a shell variable (captured, never echoed to the terminal).
GEN="$(sg docker -c "docker run --rm -e RAILS_ENV=production -e SECRET_KEY_BASE_DUMMY=1 --entrypoint sh ${MASTODON_IMAGE} -c '
  printf \"SECRET_KEY_BASE=%s\n\" \"\$(bundle exec rails secret)\"
  printf \"OTP_SECRET=%s\n\" \"\$(bundle exec rails secret)\"
  bundle exec rake mastodon:webpush:generate_vapid_key
  bundle exec rake db:encryption:init
'")"

extract() { printf '%s\n' "$GEN" | grep -m1 "^$1=" | cut -d= -f2-; }
SECRET_KEY_BASE="$(extract SECRET_KEY_BASE)"
OTP_SECRET="$(extract OTP_SECRET)"
VAPID_PRIVATE_KEY="$(extract VAPID_PRIVATE_KEY)"
VAPID_PUBLIC_KEY="$(extract VAPID_PUBLIC_KEY)"
AR_DET="$(extract ACTIVE_RECORD_ENCRYPTION_DETERMINISTIC_KEY)"
AR_SALT="$(extract ACTIVE_RECORD_ENCRYPTION_KEY_DERIVATION_SALT)"
AR_PRIM="$(extract ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY)"

for pair in SECRET_KEY_BASE OTP_SECRET VAPID_PRIVATE_KEY VAPID_PUBLIC_KEY AR_DET AR_SALT AR_PRIM; do
  if [[ -z "${!pair}" ]]; then echo "FATAL: secret generation produced empty ${pair}"; exit 1; fi
done

umask 077
cat > .env <<EOF
# GENERATED by setup.sh on $(date -u +%FT%TZ) — DO NOT COMMIT.
# Secrets generated with the Mastodon image's own tasks (rails secret,
# rake mastodon:webpush:generate_vapid_key, rake db:encryption:init).
POSTGRES_PASSWORD=$(openssl rand -hex 16)

SECRET_KEY_BASE=${SECRET_KEY_BASE}
OTP_SECRET=${OTP_SECRET}

VAPID_PRIVATE_KEY=${VAPID_PRIVATE_KEY}
VAPID_PUBLIC_KEY=${VAPID_PUBLIC_KEY}

ACTIVE_RECORD_ENCRYPTION_DETERMINISTIC_KEY=${AR_DET}
ACTIVE_RECORD_ENCRYPTION_KEY_DERIVATION_SALT=${AR_SALT}
ACTIVE_RECORD_ENCRYPTION_PRIMARY_KEY=${AR_PRIM}

# Owner admin (created by demo.sh via tootctl accounts create --role Owner).
MASTO_OWNER_USERNAME=noshit_owner
MASTO_OWNER_EMAIL=owner@localhost
# MASTO_OWNER_PASSWORD is captured from tootctl by demo.sh (appended, 0600).

# Shared known password for the deterministic seed + per-run proof accounts
# (used for web-login: CSV export, archive request, deletion confirmation).
MASTO_SEED_PASSWORD=$(openssl rand -hex 16)

# MASTO_ADMIN_TOKEN is minted by demo.sh (rails runner Doorkeeper) and appended.
EOF
chmod 600 .env
echo "[ok] wrote .env (0600) — 8 generated secrets, 0 printed"
echo "== setup complete — run ./demo.sh =="
