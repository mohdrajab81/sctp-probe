#!/usr/bin/env bash
# Run ALL tests across both repos: sentinel-cbc and sctp-probe.
#
# Usage (from WSL):
#   bash run_all_tests.sh              # full run (all suites)
#   bash run_all_tests.sh --no-live    # skip live SCTP suites (~40s instead of ~7min)
#   bash run_all_tests.sh --sentinel   # sentinel-cbc suites only
#   bash run_all_tests.sh --probe      # sctp-probe suites only
#
# Prerequisites (WSL2, auto-started by this script where possible):
#   - PostgreSQL    : started automatically if down
#   - SCTP module   : loaded automatically
#   - Docker Desktop: must be running on Windows for store/postgres suite
#                     (skipped with warning if not available)
#
# Environment variables (optional overrides):
#   SENTINEL_TEST_DSN  PostgreSQL DSN for internal/integration
#   DOCKER_HOST        Docker socket path
#   GO                 Path to go binary

set -euo pipefail

ROOT_PROBE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_SENTINEL="${ROOT_SENTINEL:-/mnt/c/Projects/sentinel-cbc}"

# ── Flags ────────────────────────────────────────────────────────────────────
RUN_LIVE=true
RUN_SENTINEL=true
RUN_PROBE=true

for arg in "$@"; do
  case "$arg" in
    --no-live)  RUN_LIVE=false ;;
    --sentinel) RUN_PROBE=false ;;
    --probe)    RUN_SENTINEL=false ;;
    -h|--help)
      grep '^#' "${BASH_SOURCE[0]}" | head -12 | sed 's/^# \?//'
      exit 0 ;;
    *) echo "Unknown flag: $arg" >&2; exit 1 ;;
  esac
done

# ── Go binary ─────────────────────────────────────────────────────────────────
GO="${GO:-}"
if [[ -z "$GO" ]]; then
  if command -v go >/dev/null 2>&1; then GO=go
  elif [[ -x /usr/local/go/bin/go ]]; then GO=/usr/local/go/bin/go
  else echo "ERROR: go not found. Set GO= or install Go." >&2; exit 1
  fi
fi

# ── pytest ────────────────────────────────────────────────────────────────────
PYTEST=""
for c in "$ROOT_PROBE/.venv-wsl/bin/pytest" "$ROOT_PROBE/.venv/bin/pytest"; do
  [[ -x "$c" ]] && PYTEST="$c" && break
done
[[ -z "$PYTEST" ]] && { echo "ERROR: pytest not found in .venv-wsl or .venv" >&2; exit 1; }

# ── PostgreSQL ────────────────────────────────────────────────────────────────
if ! pg_isready -h 127.0.0.1 -p 5432 -q 2>/dev/null; then
  echo "Starting PostgreSQL..."
  sudo service postgresql start >/dev/null
  sleep 2
fi
SENTINEL_TEST_DSN="${SENTINEL_TEST_DSN:-postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc_integration?sslmode=disable}"

# ── Docker ────────────────────────────────────────────────────────────────────
# Prefer native WSL Docker Engine; fall back to Docker Desktop bridge socket.
DOCKER_AVAILABLE=false
if [[ -z "${DOCKER_HOST:-}" ]]; then
  if [[ -S "/var/run/docker.sock" ]]; then
    export DOCKER_HOST="unix:///var/run/docker.sock"
  elif [[ -S "/mnt/wsl/docker-desktop/shared-sockets/host-services/docker.proxy.sock" ]]; then
    export DOCKER_HOST="unix:///mnt/wsl/docker-desktop/shared-sockets/host-services/docker.proxy.sock"
  fi
fi
if [[ -n "${DOCKER_HOST:-}" ]] && docker info >/dev/null 2>&1; then
  DOCKER_AVAILABLE=true
fi

# ── SCTP module ───────────────────────────────────────────────────────────────
if [[ "$RUN_LIVE" == true ]]; then
  sudo modprobe sctp 2>/dev/null || true
fi

# ── Tracking ──────────────────────────────────────────────────────────────────
declare -a RESULTS=()
TOTAL=0
PASS=0
FAIL=0

header() {
  echo ""
  echo "════════════════════════════════════════════════════════════════"
  printf "  %s\n" "$1"
  echo "════════════════════════════════════════════════════════════════"
}

record() {
  local status="$1" label="$2" n="${3:-}"
  RESULTS+=("$status  $label${n:+ ($n tests)}")
  case "$status" in
    PASS) ((PASS++)) || true; TOTAL=$((TOTAL + ${n:-0})) ;;
    FAIL) ((FAIL++)) || true; TOTAL=$((TOTAL + ${n:-0})) ;;
  esac
}

go_pass_count() {
  local f="$1" top=0 sub=0
  top=$(grep -c '^--- PASS:' "$f") || true
  sub=$(grep -c '^    --- PASS:' "$f") || true
  echo $((top + sub))
}

# ═════════════════════════════════════════════════════════════════════════════
# sentinel-cbc
# ═════════════════════════════════════════════════════════════════════════════
if [[ "$RUN_SENTINEL" == true ]]; then

  # 1. Unit tests
  header "sentinel-cbc — unit (12 packages)"
  LOG=$(mktemp /tmp/sc_unit_XXXXXX.txt)
  if (cd "$ROOT_SENTINEL" && "$GO" test -count=1 \
      ./internal/api/... ./internal/config/... ./internal/delivery/... \
      ./internal/metrics/... ./internal/protocol/... ./internal/service/... \
      ./internal/store/memory/... ./internal/transport/... \
      -v 2>&1 | tee "$LOG" | grep -E '^(ok|FAIL)\s'); then
    record PASS "sentinel-cbc unit" "$(go_pass_count "$LOG")"
  else
    record FAIL "sentinel-cbc unit"
  fi
  rm -f "$LOG"

  # 2. store/postgres (Docker testcontainers)
  header "sentinel-cbc — store/postgres (Docker)"
  if [[ "$DOCKER_AVAILABLE" == false ]]; then
    echo "  SKIP — Docker Desktop not running on Windows. Start it and re-run."
    RESULTS+=("SKIP  sentinel-cbc store/postgres (Docker not running)")
  else
    LOG=$(mktemp /tmp/sc_pg_XXXXXX.txt)
    if (cd "$ROOT_SENTINEL" && sudo DOCKER_HOST="$DOCKER_HOST" \
        "$GO" test -count=1 ./internal/store/postgres/... -v \
        2>&1 | tee "$LOG" | grep -E '^(ok|FAIL)\s'); then
      record PASS "sentinel-cbc store/postgres" "$(go_pass_count "$LOG")"
    else
      record FAIL "sentinel-cbc store/postgres"
    fi
    rm -f "$LOG"
  fi

  # 3. internal/integration (real PostgreSQL)
  header "sentinel-cbc — internal/integration (PostgreSQL)"
  LOG=$(mktemp /tmp/sc_int_XXXXXX.txt)
  if (cd "$ROOT_SENTINEL" && SENTINEL_TEST_DSN="$SENTINEL_TEST_DSN" \
      "$GO" test -count=1 ./internal/integration/... -v \
      2>&1 | tee "$LOG" | grep -E '^(ok|FAIL)\s'); then
    record PASS "sentinel-cbc internal/integration" "$(go_pass_count "$LOG")"
  else
    record FAIL "sentinel-cbc internal/integration"
  fi
  rm -f "$LOG"

  # 4. Live SCTP suite (cases 1-49)
  if [[ "$RUN_LIVE" == true ]]; then
    header "sentinel-cbc — live SCTP suite (cases 1-49)"
    LIVE_OUT=$(mktemp /tmp/sc_live_XXXXXX.txt)
    # The suite script writes a summary file; capture its stdout for counting
    bash "$ROOT_PROBE/artifacts/run_all_live_suites.sh" --all 2>&1 | tee "$LIVE_OUT"
    live_rc=${PIPESTATUS[0]}
    # Count from the summary file written by the suite script
    SUMMARY=$(ls -t "$ROOT_PROBE/artifacts/live_suite_runs_"*.txt 2>/dev/null | head -1)
    if [[ -n "$SUMMARY" ]]; then
      top=$(grep -c '^--- PASS:' "$SUMMARY") || true
      sub=$(grep -c '^    --- PASS:' "$SUMMARY") || true
      n=$((top + sub))
    else
      n=0
    fi
    if [[ $live_rc -eq 0 ]]; then
      record PASS "sentinel-cbc live SCTP suite" "$n"
    else
      record FAIL "sentinel-cbc live SCTP suite (exit=$live_rc, $n passed)"
    fi
    rm -f "$LIVE_OUT"
  else
    RESULTS+=("SKIP  sentinel-cbc live SCTP suite (--no-live)")
  fi

fi

# ═════════════════════════════════════════════════════════════════════════════
# sctp-probe
# ═════════════════════════════════════════════════════════════════════════════
if [[ "$RUN_PROBE" == true ]]; then

  # 5. sctp-probe unit tests
  header "sctp-probe — unit tests (pytest)"
  PROBE_LOG=$(mktemp /tmp/probe_unit_XXXXXX.txt)
  if (cd "$ROOT_PROBE" && "$PYTEST" tests/ \
      --ignore=tests/test_integration_phase11.py \
      -v --tb=short 2>&1 | tee "$PROBE_LOG"); then
    n=$(grep -c ' PASSED' "$PROBE_LOG") || true
    record PASS "sctp-probe unit" "$n"
  else
    record FAIL "sctp-probe unit"
  fi
  rm -f "$PROBE_LOG"

  # 6. Phase 11 integration (starts services automatically)
  if [[ "$RUN_LIVE" == true ]]; then
    header "sctp-probe — phase11 integration (live)"

    PROBE_PID="" SENTINEL_PID=""
    _cleanup_p11() {
      [[ -n "${PROBE_PID:-}"    ]] && kill "$PROBE_PID"    2>/dev/null || true
      [[ -n "${SENTINEL_PID:-}" ]] && kill "$SENTINEL_PID" 2>/dev/null || true
      fuser -k 8765/tcp 2>/dev/null || true
      fuser -k 8080/tcp 2>/dev/null || true
    }
    trap _cleanup_p11 EXIT

    fuser -k 8765/tcp 2>/dev/null || true
    fuser -k 8080/tcp 2>/dev/null || true
    sleep 1

    # Seed peer
    psql "postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable" -q -c "
      INSERT INTO peers (id,name,primary_address,secondary_address,enabled,
                         connection_state,association_id,inbound_streams,
                         outbound_streams,last_connected_at,last_disconnected_at,updated_at)
      VALUES ('sctp-probe-mme','sctp-probe MME simulator','127.0.0.1','',true,
              'DISCONNECTED',NULL,NULL,NULL,NULL,NULL,now())
      ON CONFLICT (id) DO UPDATE
        SET primary_address=EXCLUDED.primary_address,
            enabled=EXCLUDED.enabled, updated_at=now();
    " && echo "  Peer seeded"

    # Start sctp-probe
    PROBE_PYTHON=""
    for c in "$ROOT_PROBE/.venv-wsl/bin/python" "$ROOT_PROBE/.venv/bin/python"; do
      if [[ -x "$c" ]] && "$c" -c 'import sctp' 2>/dev/null; then
        PROBE_PYTHON="$c"; break
      fi
    done
    [[ -z "$PROBE_PYTHON" ]] && { echo "ERROR: no python venv with pysctp found" >&2; record FAIL "sctp-probe phase11 integration"; trap - EXIT; }

    (cd "$ROOT_PROBE" && nohup "$PROBE_PYTHON" -m uvicorn sctp_probe.main:app \
      --host 127.0.0.1 --port 8765 >/tmp/probe-p11.log 2>&1) &
    PROBE_PID=$!

    # Build + start sentinel-cbc
    SENTINEL_BIN="${SENTINELCBC_LIVE_BIN:-/tmp/sentinel-cbc-live}"
    (cd "$ROOT_SENTINEL" && "$GO" build -o "$SENTINEL_BIN" ./cmd/sentinel-cbc 2>&1)
    SENTINELCBC_DATABASE_DSN="postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable" \
    SENTINELCBC_SCTP_ENABLED=true SENTINELCBC_HTTP_PORT=8080 \
    SENTINELCBC_AUTH_ENABLED=false SENTINELCBC_CBSP_ENABLED=false \
    nohup "$SENTINEL_BIN" >/tmp/sentinel-p11.log 2>&1 &
    SENTINEL_PID=$!

    # Wait up to 20s for both services
    echo "  Waiting for services..."
    ready=false
    for i in $(seq 1 20); do
      p=false; s=false
      curl -sf http://127.0.0.1:8765/api/server/status >/dev/null 2>&1 && p=true
      curl -sf http://127.0.0.1:8080/health            >/dev/null 2>&1 && s=true
      $p && $s && ready=true && break
      sleep 1
    done

    if [[ "$ready" == false ]]; then
      echo "  ERROR: services did not start in 20s"
      echo "  probe log:    /tmp/probe-p11.log"
      echo "  sentinel log: /tmp/sentinel-p11.log"
      record FAIL "sctp-probe phase11 integration (services failed to start)"
    else
      P11_LOG=$(mktemp /tmp/probe_p11_XXXXXX.txt)
      if (cd "$ROOT_PROBE" && "$PYTEST" tests/test_integration_phase11.py \
          -v -m integration -s --tb=short 2>&1 | tee "$P11_LOG"); then
        # Count lines ending with PASSED (handles mid-line prints)
        n=$(grep -cE 'PASSED$' "$P11_LOG") || true
        record PASS "sctp-probe phase11 integration" "$n"
      else
        record FAIL "sctp-probe phase11 integration"
      fi
      rm -f "$P11_LOG"
    fi

    _cleanup_p11
    trap - EXIT
  else
    RESULTS+=("SKIP  sctp-probe phase11 integration (--no-live)")
  fi

fi

# ═════════════════════════════════════════════════════════════════════════════
# Summary
# ═════════════════════════════════════════════════════════════════════════════
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "  COMPLETE TEST RUN SUMMARY"
echo "════════════════════════════════════════════════════════════════"
for r in "${RESULTS[@]}"; do printf "  %s\n" "$r"; done
echo ""
echo "  Total tests : $TOTAL"
echo "  Suites PASS : $PASS   FAIL : $FAIL"
echo "════════════════════════════════════════════════════════════════"
echo ""

[[ $FAIL -eq 0 ]]
