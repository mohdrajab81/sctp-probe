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

usage() {
  cat <<'EOF'
Usage:
  bash /mnt/c/Projects/sctp-probe/artifacts/run_all_live_suites.sh [options]

Options:
  --all             Run every suite. This is the default.
  --single-peer     Run only the single-peer full suite.
  --multi-peer      Run only the multi-peer 9D suite.
  --multi-instance  Run only the multi-instance 9E suite.
  --timing          Run only the timing 9C suite.
  --list            Print the available suite labels and exit.
  -h, --help        Show this help.
EOF
}

print_suite_list() {
  for label in "${LABELS[@]}"; do
    echo "$label"
  done
}

declare -a SELECTED_LABELS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --all)
      SELECTED_LABELS=("${LABELS[@]}")
      ;;
    --single-peer)
      SELECTED_LABELS+=("single_peer_full")
      ;;
    --multi-peer)
      SELECTED_LABELS+=("multi_peer_9d")
      ;;
    --multi-instance)
      SELECTED_LABELS+=("multi_instance_9e")
      ;;
    --timing)
      SELECTED_LABELS+=("timing_9c")
      ;;
    --list)
      print_suite_list
      exit 0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

if [[ ${#SELECTED_LABELS[@]} -eq 0 ]]; then
  SELECTED_LABELS=("${LABELS[@]}")
fi

label_enabled() {
  local wanted="$1"
  for label in "${SELECTED_LABELS[@]}"; do
    if [[ "$label" == "$wanted" ]]; then
      return 0
    fi
  done
  return 1
}

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
  if ! label_enabled "${LABELS[$i]}"; then
    continue
  fi
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
