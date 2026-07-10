#!/usr/bin/env bash
# Optional stretch: install the official Kill Bill email-notifications plugin
# into an ALREADY-RUNNING noshit-f0-killbill stack, so invoice/payment events
# are emailed into the mailpit sink (FIXTURES §2.2 sink coupling).
#
# Why a separate script (not baked into the image): the killbill container has
# no internet egress on the internal compose network, so in-container `kpm
# install` cannot fetch. Instead we download the plugin JAR + DDL on the HOST
# (which has internet), copy the JAR in, and run KPM offline with
# --from-source-file (which lays out the OSGI bundle + plugin_identifiers.json
# correctly), load the plugin DDL, restart Kill Bill to pick up the bundle, and
# upload the per-tenant event configuration.
#
# Idempotent. Downloads are cached in ./data (gitignored). Nothing is committed.
#
# Usage: ./install-email-plugin.sh          # run after the stack is up
#        (demo.py --with-email calls this for you)
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a

PROJECT="noshit-f0-killbill"
# KB 0.24 -> email-notifications 0.8.2 (killbill-cloud plugins_directory.yml).
VER="0.8.2"
JAR_URL="https://repo1.maven.org/maven2/org/kill-bill/billing/plugin/java/killbill-email-notifications-plugin/${VER}/killbill-email-notifications-plugin-${VER}.jar"
DDL_URL="https://raw.githubusercontent.com/killbill/killbill-email-notifications-plugin/killbill-email-notifications-plugin-${VER}/src/main/resources/ddl.sql"
CACHE="./data"
JAR="${CACHE}/email-plugin-${VER}.jar"
DDL="${CACHE}/email-ddl-${VER}.sql"

dc() { sg docker -c "docker compose -p ${PROJECT} $*"; }

echo "[email-plugin] 1/6 fetch JAR + DDL (cached in ${CACHE})"
mkdir -p "${CACHE}"
[ -s "${JAR}" ] || curl -fsSL -o "${JAR}" "${JAR_URL}"
[ -s "${DDL}" ] || curl -fsSL -o "${DDL}" "${DDL_URL}"

CID="$(dc ps -q killbill | tr -d '\r')"
[ -n "${CID}" ] || { echo "[email-plugin] ERROR: killbill container not running (start the stack first)"; exit 1; }

echo "[email-plugin] 2/6 copy JAR into container + offline KPM install (v${VER})"
if dc "exec -T killbill bash -lc 'test -f /var/lib/killbill/bundles/plugins/java/email/${VER}/email-plugin.jar'" >/dev/null 2>&1; then
  echo "  already installed; skipping KPM"
else
  sg docker -c "docker cp '${JAR}' ${CID}:/tmp/email-plugin.jar"
  dc "exec -T killbill bash -lc '/opt/kpm-latest/kpm install_java_plugin email-notifications --from-source-file=/tmp/email-plugin.jar --version=${VER} --destination=/var/lib/killbill/bundles'" \
     2>&1 | grep -viE "termcap|dumb terminal" || true
fi

echo "[email-plugin] 3/6 load plugin DDL (idempotent: DROP TABLE IF EXISTS)"
dc "exec -T db mariadb -uroot -p${KB_DB_PASSWORD} killbill" < "${DDL}" 2>&1 | grep -viE "insecure|Warning" || true

echo "[email-plugin] 4/6 restart Kill Bill to load the bundle"
dc restart killbill >/dev/null

echo "[email-plugin] 5/6 wait for Kill Bill health"
for i in $(seq 1 40); do
  code="$(curl -s -o /dev/null -w '%{http_code}' -m 4 "http://127.0.0.1:${KB_API_PORT:-8080}/1.0/healthcheck" 2>/dev/null || echo 000)"
  [ "${code}" = "200" ] && { echo "  healthy"; break; }
  sleep 3
done

if [ "${NOSHIT_SKIP_TENANT_CONFIG:-}" = "1" ]; then
  echo "[email-plugin] 6/6 tenant event config: skipped (demo.py uploads it after creating the tenant)"
  echo "[email-plugin] done. SMTP is wired to mailpit:${MAILPIT_SMTP_PORT:-1025} via org.killbill.mail.smtp.* ."
  exit 0
fi

echo "[email-plugin] 6/6 upload per-tenant event config (best effort; tenant must exist)"
code="$(curl -s -o /dev/null -w '%{http_code}' \
  -u "${KB_ADMIN_USER}:${KB_ADMIN_PASSWORD}" \
  -H "X-Killbill-ApiKey:${KB_TENANT_API_KEY}" -H "X-Killbill-ApiSecret:${KB_TENANT_API_SECRET}" \
  -H "X-Killbill-CreatedBy:install-email-plugin" -H "Content-Type: text/plain" \
  -X POST "http://127.0.0.1:${KB_API_PORT:-8080}/1.0/kb/tenants/uploadPluginConfig/killbill-email-notifications" \
  --data-binary 'org.killbill.billing.plugin.email-notifications.defaultEvents=INVOICE_CREATION,INVOICE_PAYMENT_SUCCESS,SUBSCRIPTION_CANCEL' 2>/dev/null || echo 000)"
if [ "${code}" = "201" ] || [ "${code}" = "200" ]; then
  echo "  tenant event config uploaded (HTTP ${code})"
else
  echo "  tenant config not uploaded yet (HTTP ${code}); create the tenant first, then re-run or let demo.py do it"
fi
echo "[email-plugin] done. SMTP is wired to mailpit:${MAILPIT_SMTP_PORT:-1025} via org.killbill.mail.smtp.* ."
echo "                Emails render only for accounts that carry a locale (e.g. en_US)."
