#!/usr/bin/env bash
# Install Football Predictions nginx site (HTTP only).
#
# Usage:
#   sudo ./deploy/nginx/install-http.sh single 10.0.0.1
#   sudo ./deploy/nginx/install-http.sh two app.football.local api.football.local
#
# See manuals/setup/DEPLOYMENT.md

set -euo pipefail

MODE="${1:-}"
SITE_NAME="football"

if [[ -z "${MODE}" ]]; then
    echo "Usage: sudo $0 single <public-host-or-ip>" >&2
    echo "       sudo $0 two <app-host> <api-host>" >&2
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AVAILABLE="/etc/nginx/sites-available/${SITE_NAME}"
ENABLED="/etc/nginx/sites-enabled/${SITE_NAME}"
TMP="$(mktemp)"

case "${MODE}" in
    single)
        PUBLIC_HOST="${2:-}"
        if [[ -z "${PUBLIC_HOST}" ]]; then
            echo "Missing public host/IP for single mode." >&2
            exit 1
        fi
        sed "s/YOUR_PUBLIC_HOST/${PUBLIC_HOST}/g" \
            "${REPO_ROOT}/deploy/nginx/football-single-host.http.conf" > "${TMP}"
        ;;
    two)
        APP_HOST="${2:-}"
        API_HOST="${3:-}"
        if [[ -z "${APP_HOST}" || -z "${API_HOST}" ]]; then
            echo "Missing app/api hostnames for two mode." >&2
            exit 1
        fi
        sed -e "s/app\\.YOUR_DOMAIN/${APP_HOST}/g" -e "s/api\\.YOUR_DOMAIN/${API_HOST}/g" \
            "${REPO_ROOT}/deploy/nginx/football-two-hosts.http.conf" > "${TMP}"
        ;;
    *)
        echo "Unknown mode: ${MODE} (use single or two)" >&2
        exit 1
        ;;
esac

install -m 644 "${TMP}" "${AVAILABLE}"
rm -f "${TMP}"
ln -sf "${AVAILABLE}" "${ENABLED}"

nginx -t
systemctl reload nginx

echo "Installed ${AVAILABLE}"
echo "Reloaded nginx."
