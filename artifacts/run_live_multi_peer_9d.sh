#!/usr/bin/env bash
set -euo pipefail

ROOT_SENTINEL="/mnt/c/Projects/sentinel-cbc"
ROOT_PROBE="/mnt/c/Projects/sctp-probe"
PROBE_A_URL="http://127.0.0.1:8875"
PROBE_B_URL="http://127.0.0.1:8876"
PROBE_A_DB="/tmp/sctp-probe-8875.db"
PROBE_B_DB="/tmp/sctp-probe-8876.db"
SENTINEL_DSN="postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable"
OUT_DIR="$ROOT_PROBE/artifacts/live_multi_peer_captures_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$OUT_DIR"

wait_http() {
  local url="$1"
  local name="$2"
  local log_path="${3:-}"
  for _ in $(seq 1 30); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "ERROR: $name not reachable at $url" >&2
  if [[ -n "$log_path" && -f "$log_path" ]]; then
    echo "--- $name log ($log_path) ---" >&2
    tail -n 120 "$log_path" >&2 || true
  fi
  exit 1
}

wait_connected() {
  local url="$1"
  local name="$2"
  for _ in $(seq 1 20); do
    if curl -fsS "$url/api/server/status" | grep -q '"peers":\["'; then
      return 0
    fi
    sleep 1
  done
  echo "ERROR: $name did not gain an SCTP peer association" >&2
  curl -fsS "$url/api/server/status" >&2 || true
  exit 1
}

export_probe_artifacts() {
  local stem="$1"
  local probe_label="$2"
  local probe_url="$3"

  curl -fsS "$probe_url/api/export/pcap" -o "${stem}_${probe_label}.pcap"
  curl -fsS "$probe_url/api/messages" -o "${stem}_${probe_label}.json"
  printf '%s|%s|%s|%s\n' "$stem" "$probe_label" "${stem}_${probe_label}.pcap" "${stem}_${probe_label}.json" >> "$OUT_DIR/manifest.txt"
}

run_case() {
  local label="$1"
  local pattern="$2"
  local stem="$OUT_DIR/$label"

  echo "=== CASE $label ==="
  SCTP_PROBE_URLS="$PROBE_A_URL,$PROBE_B_URL" \
  SCTP_PROBE_BIND_HOSTS="127.0.0.1,127.0.0.2" \
  SENTINELCBC_LIVE_MULTI_PEER_IDS="sctp-probe-mme-a,sctp-probe-mme-b" \
  SENTINELCBC_LIVE_URL="http://127.0.0.1:8080" \
  SENTINELCBC_LIVE_DSN="$SENTINEL_DSN" \
  /usr/local/go/bin/go test ./tests/integration -run "$pattern" -count=1 -v

  export_probe_artifacts "$stem" "probe_a" "$PROBE_A_URL"
  export_probe_artifacts "$stem" "probe_b" "$PROBE_B_URL"
}

stop_listener() {
  local url="$1"
  curl -fsS -X POST "$url/api/server/stop" \
    -H "Content-Type: application/json" \
    -d '{}' >/dev/null 2>&1 || true
}

cleanup() {
  stop_listener "$PROBE_A_URL"
  stop_listener "$PROBE_B_URL"
  pkill -f "uvicorn sctp_probe.main:app --host 127.0.0.1 --port 8875" >/dev/null 2>&1 || true
  pkill -f "uvicorn sctp_probe.main:app --host 127.0.0.1 --port 8876" >/dev/null 2>&1 || true
}
trap cleanup EXIT

cleanup

cd "$ROOT_PROBE"
nohup env DB_PATH="$PROBE_A_DB" "$ROOT_PROBE/.venv/bin/python" -m uvicorn sctp_probe.main:app --host 127.0.0.1 --port 8875 >/tmp/sctp-probe-8875.log 2>&1 &
nohup env DB_PATH="$PROBE_B_DB" "$ROOT_PROBE/.venv/bin/python" -m uvicorn sctp_probe.main:app --host 127.0.0.1 --port 8876 >/tmp/sctp-probe-8876.log 2>&1 &

wait_http "$PROBE_A_URL/api/server/status" "sctp-probe A" "/tmp/sctp-probe-8875.log"
wait_http "$PROBE_B_URL/api/server/status" "sctp-probe B" "/tmp/sctp-probe-8876.log"

curl -fsS -X POST "$PROBE_A_URL/api/server/start" \
  -H "Content-Type: application/json" \
  -d '{"port":29168,"ppid":24,"host":"127.0.0.1"}' >/dev/null
curl -fsS -X POST "$PROBE_B_URL/api/server/start" \
  -H "Content-Type: application/json" \
  -d '{"port":29168,"ppid":24,"host":"127.0.0.2"}' >/dev/null

psql "$SENTINEL_DSN" <<'SQL'
INSERT INTO peers (
    id, name, primary_address, secondary_address, enabled,
    connection_state, association_id, inbound_streams, outbound_streams,
    last_connected_at, last_disconnected_at, updated_at
)
VALUES
('sctp-probe-mme-a', 'sctp-probe multi peer A', '127.0.0.1', '', true, 'DISCONNECTED', NULL, NULL, NULL, NULL, NULL, now()),
('sctp-probe-mme-b', 'sctp-probe multi peer B', '127.0.0.2', '', true, 'DISCONNECTED', NULL, NULL, NULL, NULL, NULL, now())
ON CONFLICT (id) DO UPDATE
SET primary_address = EXCLUDED.primary_address,
    enabled = EXCLUDED.enabled,
    updated_at = now();
SQL

cd "$ROOT_SENTINEL"
export SENTINELCBC_DATABASE_DSN="$SENTINEL_DSN"
export SENTINELCBC_REDIS_ADDRESS="127.0.0.1:6379"
export SENTINELCBC_SCTP_ENABLED=true
export SENTINELCBC_SCTP_PORT=29168
nohup "$ROOT_SENTINEL/sentinel-cbc" >/tmp/sentinel-cbc-9d.log 2>&1 &

wait_http "http://127.0.0.1:8080/health" "sentinel-cbc" "/tmp/sentinel-cbc-9d.log"
wait_connected "$PROBE_A_URL" "sctp-probe A"
wait_connected "$PROBE_B_URL" "sctp-probe B"

cd "$ROOT_SENTINEL"
run_case "34_multi_peer_wrr_both_success" 'TestLiveSctpProbeMultiPeerWriteReplaceBothSuccess$'
run_case "35_multi_peer_wrr_mixed_outcomes" 'TestLiveSctpProbeMultiPeerWriteReplaceMixedOutcomes$'
run_case "36_multi_peer_whole_network_enabled_peers" 'TestLiveSctpProbeMultiPeerWholeNetworkResolvesEnabledPeers$'

echo "OUT_DIR=$OUT_DIR"
echo "MANIFEST=$OUT_DIR/manifest.txt"
