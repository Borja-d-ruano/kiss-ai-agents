#!/usr/bin/env bash
set -euo pipefail
MARK="# kiss-agents-tick"
( crontab -l 2>/dev/null | grep -vF "${MARK}" || true ) | crontab -
echo "Removed kiss-agents-tick lines from crontab (if any)."
