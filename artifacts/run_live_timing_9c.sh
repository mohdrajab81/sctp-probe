#!/usr/bin/env bash
set -euo pipefail

ROOT_SENTINEL="/mnt/c/Projects/sentinel-cbc"
ROOT_PROBE="/mnt/c/Projects/sctp-probe"
SENTINEL_BIN="${SENTINELCBC_LIVE_BIN:-/tmp/sentinel-cbc-live}"

# Prefer .venv-wsl (has sctp) over .venv when running in WSL
if [[ -x "$ROOT_PROBE/.venv-wsl/bin/python" ]] && \
   "$ROOT_PROBE/.venv-wsl/bin/python" -c 'import sctp' 2>/dev/null; then
  PROBE_PYTHON="$ROOT_PROBE/.venv-wsl/bin/python"
else
  PROBE_PYTHON="$ROOT_PROBE/.venv/bin/python"
fi

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
  kill_matching "uvicorn sctp_probe.main:app --host 127.0.0.1 --port 8875"
  kill_matching "$SENTINEL_BIN"
  kill_matching "/mnt/c/Projects/sentinel-cbc/sentinel-cbc"
}
trap cleanup EXIT

kill_matching() {
  local pattern="$1"
  local pid
  for pid in $(pgrep -f -- "$pattern" 2>/dev/null || true); do
    if [[ "$pid" != "$$" ]]; then
      kill "$pid" >/dev/null 2>&1 || true
    fi
  done
}

build_sentinel_binary() {
  if ! command -v /usr/local/go/bin/go >/dev/null 2>&1; then
    echo "ERROR: /usr/local/go/bin/go not found" >&2
    exit 1
  fi
  (cd "$ROOT_SENTINEL" && /usr/local/go/bin/go build -o "$SENTINEL_BIN" ./cmd/sentinel-cbc)
}

clear_listener_ports() {
  local port
  for port in "$@"; do
    fuser -k "${port}/tcp" >/dev/null 2>&1 || true
    fuser -k "${port}/sctp" >/dev/null 2>&1 || true
  done
}

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
  SENTINELCBC_LIVE_BIN="$SENTINEL_BIN" \
  /usr/local/go/bin/go test -run "$pattern" -count=1 -v ./tests/integration

  export_probe_artifacts "$label"
}

cleanup
build_sentinel_binary
clear_listener_ports 8875 8080 29168

cd "$ROOT_PROBE"
nohup env DB_PATH="$PROBE_DB" "$PROBE_PYTHON" -m uvicorn sctp_probe.main:app --host 127.0.0.1 --port 8875 >/tmp/sctp-probe-8875-9c.log 2>&1 </dev/null &
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
nohup env SENTINELCBC_HTTP_ADDR=':8080' SENTINELCBC_DATABASE_DSN="$SENTINEL_DSN" SENTINELCBC_REDIS_ADDRESS='127.0.0.1:6379' SENTINELCBC_SCTP_ENABLED=true SENTINELCBC_SCTP_PORT=29168 "$SENTINEL_BIN" >/tmp/sentinel-cbc-9c.log 2>&1 </dev/null &
wait_http "http://127.0.0.1:8080/health" "sentinel-cbc" "/tmp/sentinel-cbc-9c.log"

run_case "42_delayed_wrr_response_no_retry" 'TestLiveSctpProbeDelayedWriteReplaceResponseSucceedsWithoutRetry$'
run_case "43_wrr_timeout_then_retry_success" 'TestLiveSctpProbeWriteReplaceTimeoutThenRetrySuccess$'
run_case "44_wrr_timeout_exhausted_terminal" 'TestLiveSctpProbeWriteReplaceTimeoutExhaustedBecomesTerminal$'
run_case "45_wrr_disconnect_then_retry_success" 'TestLiveSctpProbeWriteReplaceDisconnectThenRetrySuccess$'
run_case "46_wrr_transport_failure_exhausted_terminal" 'TestLiveSctpProbeWriteReplaceTransportFailureExhaustedBecomesTerminal$'
run_case "47_swr_timeout_then_retry_success" 'TestLiveSctpProbeStopTimeoutThenRetrySuccess$'
run_case "48_swr_timeout_exhausted_terminal" 'TestLiveSctpProbeStopTimeoutExhaustedBecomesTerminal$'
run_case "49_swr_transport_failure_exhausted_terminal" 'TestLiveSctpProbeStopTransportFailureExhaustedBecomesTerminal$'

echo "OUT_DIR=$OUT_DIR"
echo "MANIFEST=$OUT_DIR/manifest.txt"
