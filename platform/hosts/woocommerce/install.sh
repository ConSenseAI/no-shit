#!/usr/bin/env bash
# noshit-f1-woocommerce — fully scripted, non-interactive WordPress+WooCommerce
# install via the wordpress:cli image (same compose network + shared html/).
#
# Assumes the stack is UP (demo.sh gates on compose healthchecks + host HTTP
# poll before calling this). Idempotent: every step checks state first, so
# re-running against an installed store is a fast no-op.
#
# Admin credentials come from .env via the wpcli container's environment; the
# password is expanded INSIDE the container shell and is never echoed here.
set -uo pipefail
cd "$(dirname "$0")"

PROJECT=noshit-f1-woocommerce
WC_VERSION="10.9.4"   # pinned at build (wordpress.org latest, verified 2026-07-11)

wpcli() { sg docker -c "docker compose -p $PROJECT run --rm -T wpcli $1"; }

# --- core install -------------------------------------------------------------
if wpcli "wp core is-installed" >/dev/null 2>&1; then
  echo "[install] WordPress core already installed — skipping core install"
else
  echo "[install] wp core install (site title/admin creds from .env; --skip-email)"
  wpcli "sh -c 'wp core install --url=http://127.0.0.1:8083 --title=\"\$WP_SITE_TITLE\" --admin_user=\"\$WP_ADMIN_USER\" --admin_password=\"\$WP_ADMIN_PASSWORD\" --admin_email=\"\$WP_ADMIN_EMAIL\" --skip-email'" \
    || { echo "[install] FAIL: wp core install"; exit 1; }
fi

wpcli "wp core version --extra" | sed 's/^/[install]   /'

# --- WooCommerce (free, GPL, from wordpress.org — the ONLY plugin source) -----
if wpcli "wp plugin is-active woocommerce" >/dev/null 2>&1; then
  echo "[install] WooCommerce already active — skipping plugin install"
elif wpcli "wp plugin is-installed woocommerce" >/dev/null 2>&1; then
  echo "[install] WooCommerce installed but inactive — activating"
  wpcli "wp plugin activate woocommerce" || { echo "[install] FAIL: activate woocommerce"; exit 1; }
else
  echo "[install] wp plugin install woocommerce --version=$WC_VERSION --activate (from wordpress.org)"
  wpcli "wp plugin install woocommerce --version=$WC_VERSION --activate" \
    || { echo "[install] FAIL: install woocommerce"; exit 1; }
fi

wpcli "wp plugin list --fields=name,status,version" | sed 's/^/[install]   /'

# --- store configuration (idempotent; one WP boot for all options) -------------
echo "[install] configuring store (USD, no shipping, COD offline gateway, classic checkout)"
wpcli "wp eval-file /seed/configure-store.php" | sed 's/^/[install]   /' \
  || { echo "[install] FAIL: configure-store.php"; exit 1; }

# --- findings capture: the subscriptions-plugin story (README §findings) ------
# WooCommerce Subscriptions is PAID (woocommerce.com) and is NOT installed —
# ever. Record what wordpress.org offers as free stand-ins; installing one is
# optional future work and out of scope for this leg.
echo "[install] wp plugin search subscriptions (evidence only — nothing installed):"
wpcli "wp plugin search subscriptions --per-page=5 --fields=name,slug,rating,active_installs" \
  | sed 's/^/[install]   /' || echo "[install]   (plugin search unavailable — offline?)"

echo "[install] done."
