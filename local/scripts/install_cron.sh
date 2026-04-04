#!/usr/bin/env bash
set -euo pipefail
PORT="${KISS_HTTP_PORT:-8787}"
CRON="${KISS_CRON_EXPRESSION:-*/5 * * * *}"
MARK="# kiss-agents-tick"
LINE="${CRON} curl -fsS http://127.0.0.1:${PORT}/api/tick >/dev/null 2>&1 ${MARK}"
( crontab -l 2>/dev/null | grep -vF "${MARK}" || true; echo "${LINE}" ) | crontab -
echo "Crontab updated: ${LINE}"
