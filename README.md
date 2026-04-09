# sctp-probe

A standalone SCTP client/server testing tool with a web UI and REST API.
Designed as a general-purpose SBc-AP / SCTP simulator — originally built as
an MME simulator for [SentinelCBC](../sentinel-cbc).

---

## What it does

- **SCTP server** — listen on one or more ports, accept associations, capture PDUs
- **SCTP client** — connect to a remote SCTP peer, send raw bytes or named templates
- **SBc-AP decode** — decode inbound PDUs (MI, SN, cause, Warning-Area-List, etc.)
- **Auto-reply rules** — automatically respond with WRR_SUCCESS, SWR_SUCCESS, and more
- **Web UI** — three-panel browser interface with live WebSocket message log
- **REST API** — full programmatic control for automated tests
- **SQLite log** — all messages persisted across restarts; poll efficiently with `since_id`
- **Export** — JSON and PCAP (proper Ethernet/IPv4/SCTP framing, opens in Wireshark)

### Supported SBc-AP messages

**Inbound (decoded):** `WRR_REQ`, `SWR_REQ`, `ERR_IND`, `WRWI`, `SWI`, `PWS_RESTART`, `PWS_FAILURE`

**Outbound (encoded):** `WRR_RESP` (SUCCESS/PARTIAL/PERMANENT_FAILURE/TRANSIENT_FAILURE), `SWR_RESP` (SUCCESS/NOT_FOUND), `ERR_IND_SEMANTIC`, `ERR_IND_TRANSFER_SYNTAX`, `WRWI_SCHEDULED`, `WRWI_CANCELLED`, `SWI_CANCELLED`

---

## Requirements

| Requirement                        | Notes                               |
| ---------------------------------- | ----------------------------------- |
| Linux or WSL2 Ubuntu 22.04 / 24.04 | SCTP sockets require a Linux kernel |
| Python 3.11 or 3.12                | Tested on 3.12.3                    |
| `libsctp-dev`, `lksctp-tools`      | System packages                     |
| SCTP kernel module loaded          | `sudo modprobe sctp`                |

> **Windows users:** Run everything inside WSL2. The web UI and REST API are
> accessible from the Windows browser at `http://localhost:8765` — WSL2 forwards
> the port automatically.

---

## Installation

### 1. Install system packages

```bash
sudo apt update
sudo apt install -y libsctp-dev lksctp-tools python3-pip python3-venv
```

### 2. Load the SCTP kernel module

```bash
sudo modprobe sctp
checksctp          # should print: SCTP supported
```

To make it persistent across reboots:

```bash
echo sctp | sudo tee /etc/modules-load.d/sctp.conf
```

### 3. Clone and create the virtual environment

```bash
cd /mnt/c/Projects          # or wherever you want it
git clone <repo-url> sctp-probe
cd sctp-probe
python3 -m venv .venv-wsl
source .venv-wsl/bin/activate
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 5. Verify the installation

```bash
# sctp (pysctp) — SCTP socket support
python -c "import sctp; print('sctp OK')"

# pycrate — SBc-AP ASN.1 codec (compiled from specs/sbcap/*.asn)
python -c "
import sys; sys.path.insert(0, '.')
from specs.SbcAP_gen import SBC_AP_PDU_Descriptions
print('pycrate SBc-AP OK')
"
```

Both must print OK. If sctp fails, re-run `sudo modprobe sctp`.

---

## Running sctp-probe

```bash
bash scripts/start.sh
```

Or manually:

```bash
cd /mnt/c/Projects/sctp-probe
source .venv-wsl/bin/activate
uvicorn sctp_probe.main:app --host 127.0.0.1 --port 8765
```

Open `http://localhost:8765` in your browser (Windows browser works via WSL2 port
forwarding).

### Environment variables

| Variable        | Default          | Description                                                                   |
| --------------- | ---------------- | ----------------------------------------------------------------------------- |
| `WEB_PORT`      | `8765`           | HTTP / WebSocket port                                                         |
| `DB_PATH`       | `sctp_probe.db`  | SQLite file path. Use `:memory:` for ephemeral mode                           |
| `LOG_LEVEL`     | `INFO`           | Python log level (`DEBUG`, `INFO`, `WARNING`)                                 |
| `AUTO_MODPROBE` | `false`          | Set to `true` to run `modprobe sctp` on startup (requires passwordless sudo)  |

Example with all options:

```bash
LOG_LEVEL=DEBUG DB_PATH=/tmp/test.db uvicorn sctp_probe.main:app --host 127.0.0.1 --port 8765
```

---

## Usage

### Start an SCTP listener

```bash
curl -s -X POST http://127.0.0.1:8765/api/server/start \
  -H "Content-Type: application/json" \
  -d '{"port": 29168, "ppid": 24}'
```

`ppid` is the SCTP Payload Protocol Identifier. SBc-AP uses PPID 24.

Optional field `host` (or `bind_host`) chooses the local SCTP bind address.
Default is `127.0.0.1`. Used by the multi-peer live suite to run more than one
simulator instance on the same SCTP port with different loopback IPs:

```bash
curl -s -X POST http://127.0.0.1:8766/api/server/start \
  -H "Content-Type: application/json" \
  -d '{"port": 29168, "ppid": 24, "host": "127.0.0.2"}'
```

For multi-peer live testing, run each probe API instance with its own `DB_PATH`.
Using one shared SQLite file for both instances causes rule and message state to
bleed across simulators.

### Add an auto-reply rule

```bash
# Always reply WRR_SUCCESS to every WRR_REQ
curl -s -X POST http://127.0.0.1:8765/api/rules \
  -H "Content-Type: application/json" \
  -d '{
    "match_pdu_type": "WRR_REQ",
    "action": "auto_reply",
    "reply_template": "WRR_SUCCESS",
    "count": 0
  }'
```

`count: 0` means unlimited. Set `count: 1` to reply only once.

### Send a message manually

```bash
# Send raw hex bytes to all connected server peers
curl -s -X POST http://127.0.0.1:8765/api/send \
  -H "Content-Type: application/json" \
  -d '{"hex": "00 01 00 10 ..."}'

# Send a named template (echoes MI+SN from a reference message)
curl -s -X POST http://127.0.0.1:8765/api/send \
  -H "Content-Type: application/json" \
  -d '{
    "template": "WRR_SUCCESS",
    "message_identifier": "0x1144",
    "serial_number": "0x0001"
  }'
```

### Read the message log

```bash
# All messages
curl -s http://127.0.0.1:8765/api/messages | jq .

# Efficient polling — only return messages newer than id=42
curl -s "http://127.0.0.1:8765/api/messages?since_id=42" | jq .

# Filter by direction or pdu_type
curl -s "http://127.0.0.1:8765/api/messages?direction=inbound&pdu_type=WRR_REQ" | jq .
```

### Reset between tests

```bash
curl -s -X POST http://127.0.0.1:8765/api/session/reset
```

This clears all messages and rules without dropping active SCTP connections.

### Export

```bash
# JSON export
curl -s http://127.0.0.1:8765/api/export/json -o capture.json

# PCAP export (Ethernet/IPv4/SCTP framing — opens directly in Wireshark)
curl -s http://127.0.0.1:8765/api/export/pcap -o capture.pcap
```

---

## SentinelCBC Integration (MME Simulator)

This section describes using sctp-probe as a live MME simulator against a running
SentinelCBC instance.

> **Platform rule:** All live SCTP integration must run fully inside WSL2/Linux.
> SentinelCBC, sctp-probe, and PostgreSQL must all be running inside the same
> WSL2 environment. Use the checked-in bash runners in `artifacts/` — do not
> use ad hoc PowerShell backgrounding.

### Prerequisites

- SentinelCBC repo at `/mnt/c/Projects/sentinel-cbc`
- PostgreSQL running in WSL at `127.0.0.1:5432`
  (`sudo service postgresql start`)
- SCTP kernel module loaded (`sudo modprobe sctp`)
- Docker Engine running in WSL (`sudo service docker start`) — only needed for
  the `store/postgres` test suite, not for the live integration itself

### Step 1 — Start infrastructure

```bash
# Start PostgreSQL (if not already running)
sudo service postgresql start

# Load SCTP kernel module (if not already loaded)
sudo modprobe sctp
```

### Step 2 — Seed the peer into PostgreSQL

SentinelCBC loads peers once at startup via `PeerStore.List()`. The row must
exist **before** SentinelCBC starts.

```bash
psql "postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable" \
  -c "INSERT INTO peers (id, name, primary_address, secondary_address, enabled,
                         connection_state, association_id, inbound_streams, outbound_streams,
                         last_connected_at, last_disconnected_at, updated_at)
      VALUES ('sctp-probe-mme', 'sctp-probe MME simulator', '127.0.0.1', '',
              true, 'DISCONNECTED', NULL, NULL, NULL, NULL, NULL, now())
      ON CONFLICT (id) DO UPDATE
        SET primary_address = EXCLUDED.primary_address,
            enabled         = EXCLUDED.enabled,
            updated_at      = now();"
```

### Step 3 — Start sctp-probe (terminal 1)

```bash
cd /mnt/c/Projects/sctp-probe
source .venv-wsl/bin/activate
uvicorn sctp_probe.main:app --host 127.0.0.1 --port 8765
```

### Step 4 — Start the SCTP listener and add the auto-reply rule

```bash
# Start listener on the SBc-AP standard port
curl -s -X POST http://127.0.0.1:8765/api/server/start \
  -H "Content-Type: application/json" \
  -d '{"port": 29168, "ppid": 24}'

# Add WRR_SUCCESS auto-reply rule
curl -s -X POST http://127.0.0.1:8765/api/rules \
  -H "Content-Type: application/json" \
  -d '{"match_pdu_type": "WRR_REQ", "action": "auto_reply",
       "reply_template": "WRR_SUCCESS", "count": 0}'
```

### Step 5 — Start SentinelCBC with SCTP enabled (terminal 2)

```bash
cd /mnt/c/Projects/sentinel-cbc
SENTINELCBC_DATABASE_DSN="postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable" \
SENTINELCBC_SCTP_ENABLED=true \
SENTINELCBC_SCTP_PORT=29168 \
go run ./cmd/sentinel-cbc
```

Confirm in SentinelCBC logs:

```text
"sctp: peer connected" peerID=sctp-probe-mme
```

### Step 6 — Post a warning and verify

```bash
curl -s -X POST http://127.0.0.1:8080/api/v1/warnings \
  -H "Content-Type: application/json" \
  -d '{
    "family": "CMAS",
    "cmasCategory": "PRESIDENTIAL",
    "language": "en",
    "messageText": "Integration test",
    "targetScope": "SPECIFIC_AREA",
    "deliveryArea": {
      "type": "EUTRAN_TAI_LIST",
      "taiList": [{"plmn": "41601", "tacHex": "0001"}]
    },
    "broadcastBehavior": "BROADCAST_ONCE",
    "targetPeerIds": ["sctp-probe-mme"]
  }' | jq .
```

Check sctp-probe message log — expect inbound `WRR_REQ` and outbound `WRR_RESP`:

```bash
curl -s http://127.0.0.1:8765/api/messages | jq '[.messages[] | {id, direction, pdu_type, protocol}]'
```

Check dispatch state in PostgreSQL — expect `state=DONE`:

```bash
psql "postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable" \
  -c "SELECT peer_id, state FROM warning_peer_dispatches ORDER BY id DESC LIMIT 5;"
```

### Step 7 — Export PCAP for Wireshark

```bash
curl -s http://127.0.0.1:8765/api/export/pcap -o /tmp/capture.pcap
cp /tmp/capture.pcap /mnt/c/Users/<YourUser>/Desktop/capture.pcap
```

Open in Wireshark. The full `Ethernet → IPv4 → SCTP → SBc-AP` decode tree is
visible. Look for `Write-Replace-Warning-Request` with the correct
`Message-Identifier`.

---

## Running Tests

### Overview

The test suite spans both repos (sctp-probe + SentinelCBC) and totals **684 verified
passing tests**
across 6 suites. The single entry point that runs everything is `run_all_tests.sh`
at the sctp-probe repo root.

```text
684 passing tests total
├── Suite 1  sentinel-cbc unit (12 packages)          347 tests   Windows / WSL / Linux / macOS
├── Suite 2  sentinel-cbc store/postgres (Docker)      15 tests   WSL only (Docker Engine)
├── Suite 3  sentinel-cbc internal/integration        143 tests   WSL only (PostgreSQL)
├── Suite 4  sentinel-cbc live SCTP (cases 01–49)      70 tests   WSL only (SCTP + PostgreSQL)
├── Suite 5  sctp-probe unit (pytest)                 102 tests   Windows / WSL (1 skip on Windows)
└── Suite 6  sctp-probe phase11 integration             7 tests   WSL only (SCTP + PostgreSQL)
```

The overview above uses the master runner's passing-test counts. Suite 5 still
collects 103 pytest items on WSL, but one SCTP transport case skips there, so
the cross-repo headline uses 102 passing tests for that suite.

---

### Master runner — run everything

```bash
# From WSL, sctp-probe repo root
cd /mnt/c/Projects/sctp-probe

bash run_all_tests.sh                 # full run — all 684 passing tests (~20 min)
bash run_all_tests.sh --no-live       # skip live SCTP suites — ~607 passing tests (~2 min)
bash run_all_tests.sh --sentinel      # sentinel-cbc suites only (1 + 2 + 3 + 4)
bash run_all_tests.sh --probe         # sctp-probe suites only (5 + 6)
bash run_all_tests.sh -h              # show help
```

`run_all_tests.sh` handles all prerequisites automatically:

- Starts PostgreSQL if it is not running (`sudo service postgresql start`)
- Loads the SCTP kernel module (`sudo modprobe sctp`)
- Detects Docker Engine at `/var/run/docker.sock` (falls back to Docker Desktop
  socket if native Docker is not running)
- Starts and stops sctp-probe and sentinel-cbc for the phase11 suite

**Environment variable overrides (all optional):**

| Variable | Default | Purpose |
| --- | --- | --- |
| `SENTINEL_TEST_DSN` | see below | PostgreSQL DSN for internal/integration suite |
| `DOCKER_HOST` | auto-detected | Docker socket — tries `/var/run/docker.sock` then Docker Desktop socket |
| `GO` | auto-detected | Go binary — tries `go` on PATH then `/usr/local/go/bin/go` |
| `ROOT_SENTINEL` | `/mnt/c/Projects/sentinel-cbc` | Path to sentinel-cbc repo |

Default `SENTINEL_TEST_DSN`:

```text
postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc_integration?sslmode=disable
```

---

### Suite 1 — sentinel-cbc unit tests

**Nature:** Pure unit tests. No database, no Docker, no network, no SCTP. In-memory only.
**Count:** 347 tests across 12 packages.
**Platform:** Windows, WSL, Linux, macOS — anywhere Go is installed.

```bash
# From inside the sentinel-cbc repo
go test -count=1 \
  ./internal/api/... \
  ./internal/config/... \
  ./internal/delivery/... \
  ./internal/metrics/... \
  ./internal/protocol/... \
  ./internal/service/... \
  ./internal/store/memory/... \
  ./internal/transport/...

# Or via Makefile
make test
```

**Package breakdown (top-level test functions; the runner also counts subtests):**

| Package | Tests |
| --- | ---: |
| `internal/api` | 68 |
| `internal/config` | 8 |
| `internal/delivery` | 29 |
| `internal/metrics` | 1 |
| `internal/protocol` (cbs, cbsp, protocoljson, sbcap) | 79 |
| `internal/service` | 50 |
| `internal/store/memory` | 5 |
| `internal/transport` (cbsp, sctp) | 22 |
| **Top-level functions** | **262** |

The master runner counts subtests individually from verbose `go test` output,
which is why Suite 1 reports 347 passing tests even though the package table
above lists 262 top-level functions.

**Useful flags:**

- `-v` — verbose per-test output
- `-run TestFoo` — run a single test or pattern
- `-race` — race detector (needs CGO/GCC on Windows)

---

### Suite 2 — sentinel-cbc store/postgres (Docker testcontainers)

**Nature:** Integration tests for the PostgreSQL store layer. Uses testcontainers
to spin up a real `postgres:16-alpine` Docker container, runs schema migrations,
and uses Docker snapshot/restore to reset state between each test.
**Count:** 15 tests.
**Platform:** WSL only. Requires Docker Engine running (`sudo service docker start`).

```bash
# From inside the sentinel-cbc repo
sudo DOCKER_HOST=unix:///var/run/docker.sock \
  go test -count=1 ./internal/store/postgres/... -v

# Or via the sentinel-cbc standalone runner (handles Docker detection)
bash scripts/test_all.sh
```

> Note: This suite is hardwired to testcontainers by design — there is no
> `SENTINEL_TEST_DSN` override. Docker is required.

---

### Suite 3 — sentinel-cbc internal/integration (PostgreSQL)

**Nature:** Integration tests using a fake SCTP transport with a real PostgreSQL
database. Tests the full service layer end-to-end without live SCTP sockets.
**Count:** 143 tests.
**Platform:** WSL only. Requires PostgreSQL running at `127.0.0.1:5432`.

```bash
# From inside the sentinel-cbc repo
SENTINEL_TEST_DSN="postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc_integration?sslmode=disable" \
  go test -count=1 ./internal/integration/... -v

# Or via the sentinel-cbc standalone runner (sets DSN automatically)
bash scripts/test_all.sh
```

> If `SENTINEL_TEST_DSN` is not set, the suite falls back to testcontainers
> (requires Docker).

---

### Suite 4 — sentinel-cbc live SCTP suite (cases 01–49)

**Nature:** Full end-to-end live tests. Each case builds a real sentinel-cbc
binary, starts it alongside sctp-probe, sends real SBc-AP SCTP messages,
verifies DB state and protocol responses, and captures a PCAP + JSON artifact.
**Count:** 70 tests (34 Go test functions, many parameterised, run as 49 named
cases across 4 scripts).
**Platform:** WSL only. Requires SCTP kernel module, PostgreSQL, Docker Engine,
Go, and the sctp-probe Python venv with `sctp`.

**Sub-scripts and their cases:**

| Script | Cases | Go test functions | What it covers |
| --- | --- | ---: | --- |
| `artifacts/run_all_live_simulator_captures.sh` | 01–33 | 33 | Single peer — happy paths, all response templates, warning families, delivery areas, validation, edge cases |
| `artifacts/run_live_multi_peer_9d.sh` | 34–36 | 3 | Two sctp-probe instances as two separate peers, sentinel-cbc connects to both simultaneously |
| `artifacts/run_live_multi_instance_9e.sh` | 37–41 | 5 | Two sentinel-cbc instances sharing one PostgreSQL DB, no duplicate sends |
| `artifacts/run_live_timing_9c.sh` | 42–49 | 8 | Timeout, retry exhaustion, disconnect, transport failure scenarios |

**Run all 4 sub-scripts via the dispatcher:**

```bash
# From WSL
bash /mnt/c/Projects/sctp-probe/artifacts/run_all_live_suites.sh          # all 49 cases (default)
bash /mnt/c/Projects/sctp-probe/artifacts/run_all_live_suites.sh --all             # same as default
bash /mnt/c/Projects/sctp-probe/artifacts/run_all_live_suites.sh --single-peer     # cases 01-33 only
bash /mnt/c/Projects/sctp-probe/artifacts/run_all_live_suites.sh --multi-peer      # cases 34-36 only
bash /mnt/c/Projects/sctp-probe/artifacts/run_all_live_suites.sh --multi-instance  # cases 37-41 only
bash /mnt/c/Projects/sctp-probe/artifacts/run_all_live_suites.sh --timing          # cases 42-49 only
bash /mnt/c/Projects/sctp-probe/artifacts/run_all_live_suites.sh --list            # print suite labels and exit
```

**Or run individual sub-scripts directly:**

```bash
bash /mnt/c/Projects/sctp-probe/artifacts/run_all_live_simulator_captures.sh
bash /mnt/c/Projects/sctp-probe/artifacts/run_live_multi_peer_9d.sh
bash /mnt/c/Projects/sctp-probe/artifacts/run_live_multi_instance_9e.sh
bash /mnt/c/Projects/sctp-probe/artifacts/run_live_timing_9c.sh
```

**Artifacts produced per run:**
- Per case: `<label>.pcap` + `<label>.json` in a timestamped directory under `artifacts/`
- `manifest.txt` listing all captures in that run
- `artifacts/live_suite_runs_<timestamp>.md` — summary report

---

### Suite 5 — sctp-probe unit tests (pytest)

**Nature:** Unit and component tests for the sctp-probe Python application.
Covers API endpoints, SBc-AP decoder, encoder, rule engine, SQLite store,
WebSocket hub, and SCTP transport. No live services needed.
**Count:** 102 passing tests in the master runner; 103 collected — **102 pass + 1 skip** on WSL. On Windows, the 3
SCTP transport tests skip (no Linux kernel), all others pass.
**Platform:** Windows or WSL. WSL recommended for full coverage.

```bash
# From WSL (sctp-probe repo root)
.venv-wsl/bin/pytest tests/ --ignore=tests/test_integration_phase11.py -v --tb=short

# From Windows (sctp-probe repo root)
python -m pytest tests/ --ignore=tests/test_integration_phase11.py -v --tb=short

# Or via the sctp-probe standalone runner
bash scripts/run_tests.sh
```

**Test files and what they cover:**

| File | Tests | What it covers |
| --- | ---: | --- |
| `tests/test_api.py` | 17 | REST API endpoints — server, client, rules, messages, export, session reset |
| `tests/test_decoder.py` | 36 | SBc-AP APER decoder — never-raise guarantee, fixture round-trips, PDU type detection |
| `tests/test_encoder.py` | 15 | SBc-AP encoder — all reply templates, None handling, round-trip verification |
| `tests/test_phase11.py` | 7 | Auto-reply pipeline, WebSocket broadcast, store bytes serialisation |
| `tests/test_rules.py` | 12 | Rule matching — wildcard, count limiting, drop action, first-match-wins |
| `tests/test_sctp_transport.py` | 3 | Real SCTP server/client roundtrip (skipped on non-Linux) |
| `tests/test_store.py` | 13 | SQLite store — save, filter, reset, concurrent inserts |

**Useful flags:**

- `-v` — verbose per-test output
- `--tb=short` — short traceback on failure
- `-k test_name` — run a specific test by name
- `-m sctp` — run only SCTP-marked tests
- `-m "not sctp"` — explicitly skip SCTP tests

---

### Suite 6 — sctp-probe phase11 integration (live)

**Nature:** Full end-to-end live integration. Verifies a complete SBc-AP
Write-Replace-Warning cycle: sentinel-cbc → SCTP → sctp-probe → auto-reply →
PostgreSQL dispatch state → PCAP export. Writes a PCAP to the Windows Desktop
for manual Wireshark inspection.
**Count:** 7 tests.
**Platform:** WSL only. Requires live sctp-probe + sentinel-cbc + PostgreSQL +
SCTP kernel module. `run_all_tests.sh` starts and stops services automatically.

```bash
# Manually (services must already be running)
.venv-wsl/bin/pytest tests/test_integration_phase11.py -v -m integration -s --tb=short
```

**Tests:**

| Test | What it verifies |
| --- | --- |
| `test_wrr_req_received` | sctp-probe received a WRR_REQ from sentinel-cbc over real SCTP |
| `test_wrr_resp_sent` | sctp-probe sent back a WRR_SUCCESS auto-reply |
| `test_mi_sn_echoed` | Message Identifier and Serial Number are echoed correctly in the response |
| `test_no_raw_fallback` | Decoded message has proper SBc-AP fields, not a raw hex fallback |
| `test_dispatch_state_done` | PostgreSQL `warning_peer_dispatches.state = DONE` |
| `test_pcap_export_magic_bytes` | Exported PCAP has valid libpcap magic bytes |
| `test_pcap_written_to_desktop` | PCAP written to Windows Desktop for Wireshark inspection |

---

### Standalone runners (single-repo, no cross-dependency)

**sentinel-cbc only** (suites 1 + 2 + 3, no live SCTP):

```bash
# From inside the sentinel-cbc repo
bash scripts/test_all.sh              # unit + store/postgres + internal/integration
bash scripts/test_all.sh --unit-only  # unit tests only (suite 1)
```

**sctp-probe only** (suite 5, optionally suite 6):

```bash
# From inside the sctp-probe repo
bash scripts/run_tests.sh             # unit tests only (suite 5)
bash scripts/run_tests.sh --with-live # wait for live services then run suite 6
```

---

### Typical development workflow

| Situation | Command | Where | Tests run |
| --- | --- | --- | ---: |
| Editing sctp-probe Python code | `python -m pytest tests/ --ignore=tests/test_integration_phase11.py -v` | Windows or WSL | ~102 |
| Editing sentinel-cbc Go code | `go test -count=1 ./internal/...` | Windows or WSL | ~347 |
| Before committing | `bash run_all_tests.sh --no-live` | WSL | ~607 |
| Before a release / after significant changes | `bash run_all_tests.sh` | WSL | 684 |

---

## Project Structure

```text
sctp-probe/
├── sctp_probe/             # Application source
│   ├── main.py             # FastAPI app — wires all modules together
│   ├── decoder.py          # SBc-AP decode (pycrate); never raises
│   ├── encoder.py          # SBc-AP encode (reply templates); returns None on failure
│   ├── rules.py            # Rule engine — match inbound, execute auto-reply
│   ├── store.py            # SQLite persistence (asyncio.to_thread)
│   ├── sctp_server.py      # SCTP server (sctp/pysctp)
│   ├── sctp_client.py      # SCTP client (sctp/pysctp)
│   ├── session.py          # Session reset logic
│   ├── export.py           # JSON + PCAP export
│   └── ws.py               # WebSocket fan-out hub
├── specs/
│   ├── sbcap/              # 3GPP TS 29.168 V15.1.0 ASN.1 source files
│   └── SbcAP_gen.py        # Compiled pycrate module (generated from specs/sbcap/)
├── static/                 # Web UI (index.html, vanilla JS/CSS — no build step)
├── tests/                  # pytest test suite
│   ├── test_api.py
│   ├── test_decoder.py
│   ├── test_encoder.py
│   ├── test_phase11.py
│   ├── test_rules.py
│   ├── test_sctp_transport.py
│   ├── test_store.py
│   └── test_integration_phase11.py
├── artifacts/              # Live suite runners and captured outputs
│   ├── run_all_live_suites.sh               # Dispatcher — runs all 4 live sub-scripts
│   ├── run_all_live_simulator_captures.sh   # Cases 01-33 (single peer)
│   ├── run_live_multi_peer_9d.sh            # Cases 34-36 (multi peer)
│   ├── run_live_multi_instance_9e.sh        # Cases 37-41 (multi instance)
│   └── run_live_timing_9c.sh               # Cases 42-49 (timing / retry)
├── scripts/
│   ├── start.sh            # Start sctp-probe in foreground (respects env vars)
│   └── run_tests.sh        # sctp-probe-only test runner (unit + optional phase11)
├── run_all_tests.sh        # Master runner — 684 verified passing tests across both repos
├── DESIGN.md               # Full technical design (authoritative)
├── IMPLEMENTATION_PLAN.md  # Phased build plan and status
├── requirements.txt        # Python dependencies
└── requirements.lock       # Pinned versions
```

---

## REST API Quick Reference

Full API specification is in [DESIGN.md](DESIGN.md) section 8.

- `POST /api/server/start` — Start SCTP listener `{port, ppid, host?}`
- `POST /api/server/stop` — Stop listener `{port?}`
- `GET  /api/server/status` — List active listeners and connected peers
- `POST /api/client/connect` — Connect to remote SCTP peer `{host, port, ppid}`
- `POST /api/client/disconnect` — Disconnect client `{id?}`
- `GET  /api/client/status` — List active client connections
- `POST /api/rules` — Create rule
- `GET  /api/rules` — List rules
- `DELETE /api/rules/{id}` — Delete rule
- `DELETE /api/rules` — Delete all rules
- `POST /api/send` — Send bytes or template `{hex?, template?, connection_id?}`
- `GET  /api/messages` — Query message log `?since_id=N&direction=&pdu_type=&limit=`
- `DELETE /api/messages` — Clear message log
- `POST /api/session/reset` — Reset session (clear messages + rules, keep connections)
- `GET  /api/export/json` — Download JSON export `?session_id=`
- `GET  /api/export/pcap` — Download PCAP export `?session_id=`
- `WS   /ws/events` — WebSocket, receive `message` and `rule_fired` events live

### Reply templates

| Template | Description |
| --- | --- |
| `WRR_SUCCESS` | Write-Replace-Warning-Response, cause=Message accepted |
| `WRR_PARTIAL` | Write-Replace-Warning-Response, cause=Message accepted partially |
| `WRR_PERMANENT_FAILURE` | Write-Replace-Warning-Response, cause=Message refused (permanent) |
| `WRR_TRANSIENT_FAILURE` | Write-Replace-Warning-Response, cause=Message refused (transient) |
| `WRR_TIMEOUT` | No bytes sent — simulates timeout / no response |
| `SWR_SUCCESS` | Stop-Warning-Response, cause=Message accepted |
| `SWR_NOT_FOUND` | Stop-Warning-Response, cause=Warning not found |
| `ERR_IND_SEMANTIC` | Error Indication, cause=Semantic error |
| `ERR_IND_TRANSFER_SYNTAX` | Error Indication, cause=Transfer syntax error |
| `WRWI_SCHEDULED` | Write-Replace-Warning-Indication, cause=Scheduled |
| `WRWI_CANCELLED` | Write-Replace-Warning-Indication, cause=Cancelled |
| `SWI_CANCELLED` | Stop-Warning-Indication, cause=Cancelled |

---

## Design and Architecture

See [DESIGN.md](DESIGN.md) for the complete technical design including:

- Module responsibilities and dependency rules
- Full data model (Message, Rule)
- Complete REST API specification
- Rule engine matching logic
- SBc-AP message coverage and encoding details
- PCAP export format
