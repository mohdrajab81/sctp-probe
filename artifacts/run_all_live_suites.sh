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

SUMMARY_FILE="$ROOT_PROBE/artifacts/live_suite_runs_$(date +%Y%m%d_%H%M%S).txt"

for i in "${!LABELS[@]}"; do
  run_and_capture_out_dir "${LABELS[$i]}" "${SCRIPTS[$i]}" >> "$SUMMARY_FILE"
done

echo "SUMMARY_FILE=$SUMMARY_FILE"
