#!/usr/bin/env bash
set -euo pipefail

ROOT_SENTINEL="/mnt/c/Projects/sentinel-cbc"
ROOT_PROBE="/mnt/c/Projects/sctp-probe"
PROBE_URL="http://127.0.0.1:8875"
PROBE_DB="/tmp/sctp-probe-8875-9c.db"
SENTINEL_DSN="postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable"
OUT_DIR="$ROOT_PROBE/artifacts/live_timing_captures_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$OUT_DIR"

wait_http() {
  local url="$1"
  local name="$2"
  local log_path="${3:-}"
  for _ in $(seq 1 40); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "ERROR: $name not reachable at $url" >&2
  if [[ -n "$log_path" && -f "$log_path" ]]; then
    echo "--- $name log ($log_path) ---" >&2
    tail -n 200 "$log_path" >&2 || true
  fi
  exit 1
}

cleanup() {
  curl -fsS -X POST "$PROBE_URL/api/server/stop" -H "Content-Type: application/json" -d '{}' >/dev/null 2>&1 || true
  pkill -f "uvicorn sctp_probe.main:app --host 127.0.0.1 --port 8875" >/dev/null 2>&1 || true
  pkill -f "/mnt/c/Projects/sentinel-cbc/sentinel-cbc" >/dev/null 2>&1 || true
}
trap cleanup EXIT

ensure_probe_listener() {
  for _ in $(seq 1 10); do
    if curl -fsS "$PROBE_URL/api/server/status" | grep -q '"port":29168'; then
      return 0
    fi
    curl -fsS -X POST "$PROBE_URL/api/server/start" \
      -H "Content-Type: application/json" \
      -d '{"port":29168,"ppid":24,"host":"127.0.0.1"}' >/dev/null 2>&1 || true
    sleep 2
  done
  echo "ERROR: probe listener on 127.0.0.1:29168 did not start cleanly" >&2
  curl -fsS "$PROBE_URL/api/server/status" >&2 || true
  tail -n 200 /tmp/sctp-probe-8875-9c.log >&2 || true
  exit 1
}

export_probe_artifacts() {
  local label="$1"
  local stem="$OUT_DIR/$label"

  curl -fsS "$PROBE_URL/api/export/pcap" -o "${stem}.pcap"
  curl -fsS "$PROBE_URL/api/messages" -o "${stem}.json"
  printf '%s|%s|%s\n' "$label" "${stem}.pcap" "${stem}.json" >> "$OUT_DIR/manifest.txt"
}

run_case() {
  local label="$1"
  local pattern="$2"

  echo "=== CASE $label ==="
  SCTP_PROBE_URL="$PROBE_URL" \
  SENTINELCBC_LIVE_URL="http://127.0.0.1:8080" \
  SENTINELCBC_LIVE_DSN="$SENTINEL_DSN" \
  /usr/local/go/bin/go test -run "$pattern" -count=1 -v ./tests/integration

  export_probe_artifacts "$label"
}

cleanup

cd "$ROOT_PROBE"
nohup env DB_PATH="$PROBE_DB" "$ROOT_PROBE/.venv/bin/python" -m uvicorn sctp_probe.main:app --host 127.0.0.1 --port 8875 >/tmp/sctp-probe-8875-9c.log 2>&1 </dev/null &
wait_http "$PROBE_URL/api/server/status" "sctp-probe" "/tmp/sctp-probe-8875-9c.log"
ensure_probe_listener

psql "$SENTINEL_DSN" <<'SQL'
INSERT INTO peers (
    id, name, primary_address, secondary_address, enabled,
    connection_state, association_id, inbound_streams, outbound_streams,
    last_connected_at, last_disconnected_at, updated_at
)
VALUES
('sctp-probe-mme', 'sctp-probe timing peer', '127.0.0.1', '', true, 'DISCONNECTED', NULL, NULL, NULL, NULL, NULL, now())
ON CONFLICT (id) DO UPDATE
SET primary_address = EXCLUDED.primary_address,
    enabled = EXCLUDED.enabled,
    updated_at = now();
SQL

cd "$ROOT_SENTINEL"
nohup env SENTINELCBC_HTTP_ADDR=':8080' SENTINELCBC_DATABASE_DSN="$SENTINEL_DSN" SENTINELCBC_REDIS_ADDRESS='127.0.0.1:6379' SENTINELCBC_SCTP_ENABLED=true SENTINELCBC_SCTP_PORT=29168 "$ROOT_SENTINEL/sentinel-cbc" >/tmp/sentinel-cbc-9c.log 2>&1 </dev/null &
wait_http "http://127.0.0.1:8080/health" "sentinel-cbc" "/tmp/sentinel-cbc-9c.log"

run_case "42_delayed_wrr_response_no_retry" 'TestLiveSctpProbeDelayedWriteReplaceResponseSucceedsWithoutRetry$'
run_case "43_wrr_timeout_then_retry_success" 'TestLiveSctpProbeWriteReplaceTimeoutThenRetrySuccess$'
run_case "44_wrr_timeout_exhausted_terminal" 'TestLiveSctpProbeWriteReplaceTimeoutExhaustedBecomesTerminal$'
run_case "45_wrr_disconnect_then_retry_success" 'TestLiveSctpProbeWriteReplaceDisconnectThenRetrySuccess$'
run_case "46_wrr_transport_failure_exhausted_terminal" 'TestLiveSctpProbeWriteReplaceTransportFailureExhaustedBecomesTerminal$'
run_case "47_swr_timeout_then_retry_success" 'TestLiveSctpProbeStopTimeoutThenRetrySuccess$'
run_case "48_swr_timeout_exhausted_terminal" 'TestLiveSctpProbeStopTimeoutExhaustedBecomesTerminal$'

echo "OUT_DIR=$OUT_DIR"
echo "MANIFEST=$OUT_DIR/manifest.txt"
