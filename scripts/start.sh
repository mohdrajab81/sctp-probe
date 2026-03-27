#!/bin/bash
# Start sctp-probe (blocking — runs in foreground).
# Run from the repo root: bash scripts/start.sh
#
# Environment variables (all optional):
#   WEB_PORT     HTTP port (default 8765)
#   DB_PATH      SQLite path (default sctp_probe.db)
#   LOG_LEVEL    DEBUG | INFO | WARNING (default INFO)

set -e
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  echo "ERROR: .venv not found. Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

source .venv/bin/activate

WEB_PORT="${WEB_PORT:-8765}"
DB_PATH="${DB_PATH:-sctp_probe.db}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"
BIND_HOST="${BIND_HOST:-0.0.0.0}"

# Detect WSL and print the reachable Windows URL
if grep -qi microsoft /proc/version 2>/dev/null; then
  WSL_IP=$(hostname -I | awk '{print $1}')
  echo "Starting sctp-probe — open in Windows browser: http://${WSL_IP}:${WEB_PORT}"
else
  echo "Starting sctp-probe on http://${BIND_HOST}:${WEB_PORT}  DB=${DB_PATH}"
fi

LOG_LEVEL="$LOG_LEVEL" DB_PATH="$DB_PATH" \
  uvicorn sctp_probe.main:app --host "$BIND_HOST" --port "$WEB_PORT"
