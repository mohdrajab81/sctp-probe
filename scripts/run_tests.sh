#!/usr/bin/env bash
# Run the complete sctp-probe test suite.
#
# Suites:
#   1. Unit tests  — all tests except phase11 integration
#   2. Phase 11    — live end-to-end (sctp-probe + sentinel-cbc must be running)
#
# Prerequisites:
#   - .venv-wsl virtualenv with dependencies installed (WSL)
#     OR .venv virtualenv (native Linux / macOS)
#   - For phase11: sctp-probe running at http://127.0.0.1:8765
#                  sentinel-cbc running at http://127.0.0.1:8080
#                  PostgreSQL at 127.0.0.1:5432
#
# Usage:
#   bash scripts/run_tests.sh                # unit only (phase11 skips if services down)
#   bash scripts/run_tests.sh --with-live    # wait for live services and run phase11
#
# Environment variables:
#   PROBE_URL     — sctp-probe URL (default: http://127.0.0.1:8765)
#   SENTINEL_URL  — sentinel-cbc URL (default: http://127.0.0.1:8080)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Virtualenv ────────────────────────────────────────────────────────────────
PYTEST=""
for candidate in "$ROOT/.venv-wsl/bin/pytest" "$ROOT/.venv/bin/pytest"; do
  if [[ -x "$candidate" ]]; then
    PYTEST="$candidate"
    break
  fi
done
if [[ -z "$PYTEST" ]]; then
  echo "ERROR: pytest not found. Expected .venv-wsl/bin/pytest or .venv/bin/pytest" >&2
  echo "Run: python3 -m venv .venv-wsl && .venv-wsl/bin/pip install -r requirements.txt" >&2
  exit 1
fi

# ── Flags ────────────────────────────────────────────────────────────────────
WITH_LIVE=false
for arg in "$@"; do
  case "$arg" in
    --with-live) WITH_LIVE=true ;;
    *) echo "Unknown flag: $arg" >&2; exit 1 ;;
  esac
done

PASS=0
FAIL=0
RESULTS=()

run_suite() {
  local label="$1"; shift
  echo ""
  echo "════════════════════════════════════════════════════════"
  echo "  Suite: $label"
  echo "════════════════════════════════════════════════════════"
  if "$@"; then
    RESULTS+=("PASS  $label")
    ((PASS++)) || true
  else
    RESULTS+=("FAIL  $label")
    ((FAIL++)) || true
  fi
}

# ── Suite 1: Unit tests ───────────────────────────────────────────────────────
cd "$ROOT"
run_suite "sctp-probe unit" \
  "$PYTEST" tests/ --ignore=tests/test_integration_phase11.py -v --tb=short

# ── Suite 2: Phase 11 integration ────────────────────────────────────────────
PROBE_URL="${PROBE_URL:-http://127.0.0.1:8765}"
SENTINEL_URL="${SENTINEL_URL:-http://127.0.0.1:8080}"

probe_up()    { curl -sf "$PROBE_URL/api/server/status" >/dev/null 2>&1; }
sentinel_up() { curl -sf "$SENTINEL_URL/health"         >/dev/null 2>&1; }

if [[ "$WITH_LIVE" == true ]]; then
  echo ""
  echo "  Waiting for live services (--with-live)..."
  for i in $(seq 1 30); do
    probe_up && sentinel_up && break
    echo "  [$i/30] waiting for sctp-probe ($PROBE_URL) and sentinel-cbc ($SENTINEL_URL)..."
    sleep 2
  done
fi

if probe_up && sentinel_up; then
  run_suite "sctp-probe phase11 integration (live)" \
    "$PYTEST" tests/test_integration_phase11.py -v -m integration -s --tb=short
else
  echo ""
  echo "  Suite: sctp-probe phase11 integration (live)"
  echo "  SKIP — services not running at $PROBE_URL and $SENTINEL_URL"
  echo "         Start both services and re-run with --with-live, or use run_all_tests.sh"
  RESULTS+=("SKIP  sctp-probe phase11 integration (live — services not running)")
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════"
echo "  sctp-probe test summary"
echo "════════════════════════════════════════════════════════"
for r in "${RESULTS[@]}"; do echo "  $r"; done
echo "  Suites passed: $PASS  failed: $FAIL"
echo ""

[[ $FAIL -eq 0 ]]
