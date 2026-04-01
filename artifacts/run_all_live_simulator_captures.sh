#!/usr/bin/env bash
set -euo pipefail

ROOT_SENTINEL="/mnt/c/Projects/sentinel-cbc"
ROOT_PROBE="/mnt/c/Projects/sctp-probe"
SENTINEL_BIN="${SENTINELCBC_LIVE_BIN:-/tmp/sentinel-cbc-live}"
OUT_DIR="$ROOT_PROBE/artifacts/live_simulator_captures_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$OUT_DIR"

cleanup() {
  kill_matching "uvicorn sctp_probe.main:app"
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

cleanup
build_sentinel_binary
clear_listener_ports 8765 8080 29168

psql "postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable" <<'SQL'
INSERT INTO peers (
    id, name, primary_address, secondary_address, enabled,
    connection_state, association_id, inbound_streams, outbound_streams,
    last_connected_at, last_disconnected_at, updated_at
)
VALUES (
    'sctp-probe-mme', 'sctp-probe live integration peer', '127.0.0.1', '', true,
    'DISCONNECTED', NULL, NULL, NULL, NULL, NULL, now()
)
ON CONFLICT (id) DO UPDATE
SET primary_address = EXCLUDED.primary_address,
    enabled = EXCLUDED.enabled,
    updated_at = now();
SQL

cd "$ROOT_PROBE"
"$ROOT_PROBE/.venv/bin/python" -m uvicorn sctp_probe.main:app --host 127.0.0.1 --port 8765 >/tmp/sctp-probe-live-suite.log 2>&1 &

export SENTINELCBC_DATABASE_DSN="postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable"
export SENTINELCBC_REDIS_ADDRESS="127.0.0.1:6379"
export SENTINELCBC_SCTP_ENABLED=true
export SENTINELCBC_SCTP_PORT=29168
export SENTINELCBC_LIVE_BIN="$SENTINEL_BIN"
"$SENTINEL_BIN" >/tmp/sentinel-cbc-live-suite.log 2>&1 &

wait_http "http://127.0.0.1:8765/api/server/status" "sctp-probe" "/tmp/sctp-probe-live-suite.log"
wait_http "http://127.0.0.1:8080/health" "sentinel-cbc" "/tmp/sentinel-cbc-live-suite.log"

cd "$ROOT_SENTINEL"

run_case() {
  local label="$1"
  local pattern="$2"
  local stem="$OUT_DIR/$label"

  echo "=== CASE $label ==="
  SCTP_PROBE_URL=http://127.0.0.1:8765 \
  SENTINELCBC_LIVE_URL=http://127.0.0.1:8080 \
  SENTINELCBC_LIVE_DSN="postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable" \
  SENTINELCBC_LIVE_BIN="$SENTINEL_BIN" \
  /usr/local/go/bin/go test ./tests/integration -run "$pattern" -count=1 -v

  curl -fsS http://127.0.0.1:8765/api/export/pcap -o "${stem}.pcap"
  curl -fsS http://127.0.0.1:8765/api/messages -o "${stem}.json"

  printf '%s|%s|%s\n' "$label" "${stem}.pcap" "${stem}.json" >> "$OUT_DIR/manifest.txt"
}

run_case "01_write_replace_happy_path" 'TestLiveSctpProbeWriteReplaceHappyPath$'
run_case "02_stop_warning_happy_path" 'TestLiveSctpProbeStopWarningHappyPath$'
run_case "03_write_replace_indication_happy_path" 'TestLiveSctpProbeWriteReplaceIndicationHappyPath$'
run_case "04_stop_warning_indication_happy_path" 'TestLiveSctpProbeStopWarningIndicationHappyPath$'
run_case "05_error_indication_happy_path" 'TestLiveSctpProbeErrorIndicationHappyPath$'

run_case "06_dispatch_wrr_success" 'TestLiveSctpProbeDispatchResponseMatrix/WRR_SUCCESS$'
run_case "07_dispatch_wrr_partial" 'TestLiveSctpProbeDispatchResponseMatrix/WRR_PARTIAL$'
run_case "08_dispatch_wrr_permanent_failure" 'TestLiveSctpProbeDispatchResponseMatrix/WRR_PERMANENT_FAILURE$'
run_case "09_dispatch_wrr_transient_failure" 'TestLiveSctpProbeDispatchResponseMatrix/WRR_TRANSIENT_FAILURE$'
run_case "10_dispatch_swr_success" 'TestLiveSctpProbeDispatchResponseMatrix/SWR_SUCCESS$'
run_case "11_dispatch_swr_not_found" 'TestLiveSctpProbeDispatchResponseMatrix/SWR_NOT_FOUND$'

run_case "12_family_cmas_presidential" 'TestLiveSctpProbeWarningFamilyMatrix/CMAS_PRESIDENTIAL$'
run_case "13_family_cmas_public_safety" 'TestLiveSctpProbeWarningFamilyMatrix/CMAS_PUBLIC_SAFETY$'
run_case "14_family_etws_primary_only" 'TestLiveSctpProbeWarningFamilyMatrix/ETWS_PRIMARY_ONLY$'
run_case "15_family_etws_with_message_body" 'TestLiveSctpProbeWarningFamilyMatrix/ETWS_WITH_MESSAGE_BODY$'
run_case "16_family_eu_alert" 'TestLiveSctpProbeWarningFamilyMatrix/EU_ALERT$'
run_case "17_family_operator_defined" 'TestLiveSctpProbeWarningFamilyMatrix/OPERATOR_DEFINED$'
run_case "18_delivery_area_tai_list_multiple" 'TestLiveSctpProbeDeliveryAreaMatrix/TAI_LIST_MULTIPLE$'
run_case "19_delivery_area_cell_list_single" 'TestLiveSctpProbeDeliveryAreaMatrix/EUTRAN_CELL_LIST_SINGLE$'
run_case "20_delivery_area_cell_list_multiple" 'TestLiveSctpProbeDeliveryAreaMatrix/EUTRAN_CELL_LIST_MULTIPLE$'
run_case "21_multiple_warnings_sequential_same_peer" 'TestLiveSctpProbeMultipleWarningsMatrix/SEQUENTIAL_SAME_PEER_TWO_WARNINGS$'
run_case "22_create_validation_whole_network_with_delivery_area" 'TestLiveSctpProbeCreateValidationMatrix/whole_network_with_delivery_area$'
run_case "23_create_validation_specific_area_without_delivery_area" 'TestLiveSctpProbeCreateValidationMatrix/specific_area_without_delivery_area$'
run_case "24_create_validation_too_many_tais" 'TestLiveSctpProbeCreateValidationMatrix/too_many_tais$'
run_case "25_stop_validation_invalid_delivery_area_type" 'TestLiveSctpProbeStopValidationMatrix/invalid_stop_delivery_area_type$'
run_case "26_stop_validation_already_stopped_conflict" 'TestLiveSctpProbeStopValidationMatrix/already_stopped_conflict$'
run_case "27_wrwi_after_stop_uncorrelated" 'TestLiveSctpProbeWriteReplaceIndicationAfterStopIsUncorrelated$'
run_case "28_error_indication_ambiguous_uncorrelated" 'TestLiveSctpProbeErrorIndicationAmbiguousUncorrelated$'
run_case "29_duplicate_wrwi_logs_twice" 'TestLiveSctpProbeDuplicateWriteReplaceIndicationLogsTwice$'
run_case "30_swi_before_stop_uncorrelated" 'TestLiveSctpProbeStopWarningIndicationBeforeStopIsUncorrelated$'
run_case "31_duplicate_swi_logs_twice" 'TestLiveSctpProbeDuplicateStopWarningIndicationLogsTwice$'
run_case "32_malformed_inbound_pdu_discarded" 'TestLiveSctpProbeMalformedInboundPDUIsDiscarded$'
run_case "33_unsupported_inbound_initiating_message_discarded" 'TestLiveSctpProbeUnsupportedInboundInitiatingMessageIsDiscarded$'

echo "OUT_DIR=$OUT_DIR"
echo "MANIFEST=$OUT_DIR/manifest.txt"
