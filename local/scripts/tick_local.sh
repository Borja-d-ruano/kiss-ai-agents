#!/usr/bin/env bash
set -euo pipefail
PORT="${KISS_HTTP_PORT:-8787}"
exec curl -fsS -X POST "http://127.0.0.1:${PORT}/api/tick"
