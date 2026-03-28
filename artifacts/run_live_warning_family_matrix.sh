#!/usr/bin/env bash
set -euo pipefail

pkill -f "uvicorn sctp_probe.main:app" || true
pkill -f "/mnt/c/Projects/sentinel-cbc/sentinel-cbc|sentinel-cbc" || true

cd /mnt/c/Projects/sctp-probe
/mnt/c/Projects/sctp-probe/.venv/bin/python -m uvicorn sctp_probe.main:app --host 127.0.0.1 --port 8765 >/tmp/sctp-probe-live.log 2>&1 &
probe_pid=$!

cleanup() {
  kill "$probe_pid" >/dev/null 2>&1 || true
  pkill -f "uvicorn sctp_probe.main:app" >/dev/null 2>&1 || true
  pkill -f "/mnt/c/Projects/sentinel-cbc/sentinel-cbc|sentinel-cbc" >/dev/null 2>&1 || true
}
trap cleanup EXIT

export SENTINELCBC_DATABASE_DSN="postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable"
export SENTINELCBC_REDIS_ADDRESS="127.0.0.1:6379"
export SENTINELCBC_SCTP_ENABLED=true
export SENTINELCBC_SCTP_PORT=29168
/mnt/c/Projects/sentinel-cbc/sentinel-cbc >/tmp/sentinel-cbc-live.log 2>&1 &

for _ in $(seq 1 15); do
  curl -fsS http://127.0.0.1:8765/api/server/status >/dev/null && break
  sleep 1
done

for _ in $(seq 1 15); do
  curl -fsS http://127.0.0.1:8080/health >/dev/null && break
  sleep 1
done

cd /mnt/c/Projects/sentinel-cbc
SCTP_PROBE_URL=http://127.0.0.1:8765 \
SENTINELCBC_LIVE_URL=http://127.0.0.1:8080 \
SENTINELCBC_LIVE_DSN="postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable" \
/usr/local/go/bin/go test ./tests/integration -run TestLiveSctpProbeWarningFamilyMatrix -count=1 -v

mkdir -p /mnt/c/Projects/sctp-probe/artifacts
curl -fsS http://127.0.0.1:8765/api/export/pcap -o /mnt/c/Projects/sctp-probe/artifacts/live_warning_family_matrix_20260328.pcap
curl -fsS http://127.0.0.1:8765/api/messages -o /mnt/c/Projects/sctp-probe/artifacts/live_warning_family_matrix_20260328_messages.json

echo "PCAP=/mnt/c/Projects/sctp-probe/artifacts/live_warning_family_matrix_20260328.pcap"
echo "JSON=/mnt/c/Projects/sctp-probe/artifacts/live_warning_family_matrix_20260328_messages.json"
echo "PROBE_TAIL"
tail -n 20 /tmp/sctp-probe-live.log || true
echo "SENTINEL_TAIL"
tail -n 20 /tmp/sentinel-cbc-live.log || true
