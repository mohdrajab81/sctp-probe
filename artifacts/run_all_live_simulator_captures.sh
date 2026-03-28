#!/usr/bin/env bash
set -euo pipefail

ROOT_SENTINEL="/mnt/c/Projects/sentinel-cbc"
ROOT_PROBE="/mnt/c/Projects/sctp-probe"
OUT_DIR="$ROOT_PROBE/artifacts/live_simulator_captures_$(date +%Y%m%d_%H%M%S)"

mkdir -p "$OUT_DIR"

cleanup() {
  pkill -f "uvicorn sctp_probe.main:app" >/dev/null 2>&1 || true
  pkill -f "/mnt/c/Projects/sentinel-cbc/sentinel-cbc|sentinel-cbc" >/dev/null 2>&1 || true
}
trap cleanup EXIT

cleanup

cd "$ROOT_PROBE"
"$ROOT_PROBE/.venv/bin/python" -m uvicorn sctp_probe.main:app --host 127.0.0.1 --port 8765 >/tmp/sctp-probe-live-suite.log 2>&1 &

export SENTINELCBC_DATABASE_DSN="postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable"
export SENTINELCBC_REDIS_ADDRESS="127.0.0.1:6379"
export SENTINELCBC_SCTP_ENABLED=true
export SENTINELCBC_SCTP_PORT=29168
"$ROOT_SENTINEL/sentinel-cbc" >/tmp/sentinel-cbc-live-suite.log 2>&1 &

for _ in $(seq 1 20); do
  curl -fsS http://127.0.0.1:8765/api/server/status >/dev/null && break
  sleep 1
done

for _ in $(seq 1 20); do
  curl -fsS http://127.0.0.1:8080/health >/dev/null && break
  sleep 1
done

cd "$ROOT_SENTINEL"

run_case() {
  local label="$1"
  local pattern="$2"
  local stem="$OUT_DIR/$label"

  echo "=== CASE $label ==="
  SCTP_PROBE_URL=http://127.0.0.1:8765 \
  SENTINELCBC_LIVE_URL=http://127.0.0.1:8080 \
  SENTINELCBC_LIVE_DSN="postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable" \
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

echo "OUT_DIR=$OUT_DIR"
echo "MANIFEST=$OUT_DIR/manifest.txt"
