#!/usr/bin/env bash
set -euo pipefail

ROOT_PROBE="/mnt/c/Projects/sctp-probe"

declare -a LABELS=(
  "single_peer_full"
  "multi_peer_9d"
  "multi_instance_9e"
  "timing_9c"
)

declare -a SCRIPTS=(
  "$ROOT_PROBE/artifacts/run_all_live_simulator_captures.sh"
  "$ROOT_PROBE/artifacts/run_live_multi_peer_9d.sh"
  "$ROOT_PROBE/artifacts/run_live_multi_instance_9e.sh"
  "$ROOT_PROBE/artifacts/run_live_timing_9c.sh"
)

run_and_capture_out_dir() {
  local label="$1"
  local script_path="$2"
  local log_path="/tmp/${label}.log"

  echo "=== RUN $label ==="
  bash "$script_path" | tee "$log_path"

  local out_dir
  out_dir="$(grep '^OUT_DIR=' "$log_path" | tail -n 1 | cut -d'=' -f2- || true)"
  if [[ -z "$out_dir" ]]; then
    echo "ERROR: $label did not report OUT_DIR" >&2
    tail -n 120 "$log_path" >&2 || true
    exit 1
  fi
  printf '%s|%s\n' "$label" "$out_dir"
}

count_manifest_lines() {
  local manifest_path="$1"
  if [[ -f "$manifest_path" ]]; then
    wc -l < "$manifest_path" | tr -d ' '
  else
    echo "0"
  fi
}

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
SUMMARY_FILE="$ROOT_PROBE/artifacts/live_suite_runs_${TIMESTAMP}.txt"
REPORT_FILE="$ROOT_PROBE/artifacts/live_suite_runs_${TIMESTAMP}.md"

{
  echo "# Live Suite Run Summary"
  echo
  echo "Generated at: $(date -Iseconds)"
  echo
  echo "| Suite | Output Directory | Manifest | Entries |"
  echo "| --- | --- | --- | ---: |"
} > "$REPORT_FILE"

for i in "${!LABELS[@]}"; do
  result="$(run_and_capture_out_dir "${LABELS[$i]}" "${SCRIPTS[$i]}")"
  echo "$result" >> "$SUMMARY_FILE"

  label="${result%%|*}"
  out_dir="${result#*|}"
  manifest_path="${out_dir}/manifest.txt"
  entry_count="$(count_manifest_lines "$manifest_path")"
  printf '| %s | %s | %s | %s |\n' "$label" "$out_dir" "$manifest_path" "$entry_count" >> "$REPORT_FILE"
done

echo "SUMMARY_FILE=$SUMMARY_FILE"
echo "REPORT_FILE=$REPORT_FILE"
