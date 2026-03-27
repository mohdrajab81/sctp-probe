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

**Outbound (encoded):** `WRR_RESP` (SUCCESS/PARTIAL/FAILURE/TIMEOUT), `SWR_RESP`, `ERR_IND_SEMANTIC`, `ERR_IND_TRANSFER_SYNTAX`, `WRWI_SCHEDULED`, `WRWI_CANCELLED`, `SWI_CANCELLED`

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
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 5. Verify the installation

```bash
# pysctp — SCTP socket support
python -c "import sctp; print('pysctp OK')"

# pycrate — SBc-AP ASN.1 codec (compiled from specs/sbcap/*.asn)
python -c "
import sys; sys.path.insert(0, '.')
from specs.SbcAP_gen import SBC_AP_PDU_Descriptions
print('pycrate SBc-AP OK')
"
```

Both must print OK. If pysctp fails, re-run `sudo modprobe sctp`.

---

## Running sctp-probe

```bash
bash scripts/start.sh
```

Or manually:

```bash
cd /mnt/c/Projects/sctp-probe
source .venv/bin/activate
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
SentinelCBC instance. It mirrors the steps in `IMPLEMENTATION_PLAN.md` Phase 11.

### Prerequisites

- SentinelCBC repo at `/mnt/c/Projects/sentinel-cbc`
- Docker (for Postgres + Redis): `docker compose ... up -d postgres redis`
- Both services accessible at `127.0.0.1`

### Step 1 — Start infrastructure

```bash
cd /mnt/c/Projects/sentinel-cbc
docker compose -f deployments/docker/docker-compose.yaml up -d postgres redis
docker compose -f deployments/docker/docker-compose.yaml ps
```

Wait until both containers show `running` or `healthy`.

### Step 2 — Seed the peer into Postgres

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
source .venv/bin/activate
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
SENTINELCBC_REDIS_ADDRESS="127.0.0.1:6379" \
SENTINELCBC_SCTP_ENABLED=true \
SENTINELCBC_SCTP_PORT=29168 \
./sentinel-cbc
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
    "urgency": "IMMEDIATE",
    "certainty": "OBSERVED",
    "language": "en",
    "messageText": "Integration test",
    "targetScope": "SPECIFIC_AREA",
    "deliveryArea": {
      "type": "TAI_LIST",
      "taiList": [{"plmn": "41601", "tacHex": "0001"}]
    },
    "broadcastBehavior": "BROADCAST_ONCE",
    "targetPeerIds": ["sctp-probe-mme"]
  }' | jq .
```

Check sctp-probe message log — expect inbound `WRR_REQ` and outbound `WRR_RESP`,
both with `protocol=SBc-AP`:

```bash
curl -s http://127.0.0.1:8765/api/messages | jq '[.messages[] | {id, direction, pdu_type, protocol}]'
```

Check dispatch state in Postgres — expect `state=DONE`:

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

```bash
# Quick (non-SCTP, any OS)
bash scripts/run_tests.sh

# All tests including SCTP (Linux/WSL2 with SCTP module loaded)
source .venv/bin/activate && pytest tests/ -v

# Full live integration test (requires sctp-probe + SentinelCBC + Postgres running)
pytest tests/test_integration_phase11.py -v -m integration -s

# Validate pycrate decoder against SentinelCBC fixture corpus
python tests/validate_fixtures.py \
  --fixtures-dir ../sentinel-cbc/schemas/protocol/fixtures
```

### Test files

- `tests/test_decoder.py` — SBc-AP decode for all supported PDU types
- `tests/test_encoder.py` — SBc-AP encode for all reply templates
- `tests/test_store.py` — SQLite store operations
- `tests/test_rules.py` — Rule engine matching and auto-reply logic
- `tests/test_api.py` — FastAPI REST endpoints (mocked SCTP)
- `tests/test_sctp_transport.py` — Real SCTP socket roundtrip (`-m sctp`)
- `tests/test_phase11.py` — Phase 11 regression tests (bytes serialisation, outbound logging, WS broadcast)
- `tests/test_integration_phase11.py` — Full live integration test (`-m integration`)
- `tests/validate_fixtures.py` — CLI: decode `.bin` fixtures and compare to `.expected.json`

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
│   ├── sctp_server.py      # SCTP server (pysctp)
│   ├── sctp_client.py      # SCTP client (pysctp)
│   ├── session.py          # Session reset logic
│   ├── export.py           # JSON + PCAP export
│   └── ws.py               # WebSocket fan-out hub
├── specs/
│   ├── sbcap/              # 3GPP TS 29.168 V15.1.0 ASN.1 source files
│   └── SbcAP_gen.py        # Compiled pycrate module (generated from specs/sbcap/)
├── static/                 # Web UI (index.html, vanilla JS/CSS — no build step)
├── tests/                  # pytest test suite
├── scripts/
│   ├── start.sh            # Start sctp-probe (blocking, respects env vars)
│   └── run_tests.sh        # Run non-SCTP tests (any OS)
├── DESIGN.md               # Full technical design (authoritative)
├── IMPLEMENTATION_PLAN.md  # Phased build plan and status
├── requirements.txt        # Python dependencies
└── requirements.lock       # Pinned versions
```

---

## REST API Quick Reference

Full API specification is in [DESIGN.md](DESIGN.md) section 8.

- `POST /api/server/start` — Start SCTP listener `{port, ppid}`
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

- `WRR_SUCCESS` — Write-Replace-Warning-Response, cause=Message accepted
- `WRR_PARTIAL` — Write-Replace-Warning-Response, cause=Message accepted partially
- `WRR_FAILURE` — Write-Replace-Warning-Response, cause=Message refused
- `WRR_TIMEOUT` — No bytes sent (simulates timeout / no response)
- `SWR_SUCCESS` — Stop-Warning-Response, cause=Message accepted
- `SWR_FAILURE` — Stop-Warning-Response, cause=Message refused
- `ERR_IND_SEMANTIC` — Error Indication, cause=Semantic error
- `ERR_IND_TRANSFER_SYNTAX` — Error Indication, cause=Transfer syntax error
- `WRWI_SCHEDULED` — Write-Replace-Warning-Indication, cause=Scheduled
- `WRWI_CANCELLED` — Write-Replace-Warning-Indication, cause=Cancelled
- `SWI_CANCELLED` — Stop-Warning-Indication, cause=Cancelled

---

## Design and Architecture

See [DESIGN.md](DESIGN.md) for the complete technical design including:

- Module responsibilities and dependency rules
- Full data model (Message, Rule)
- Complete REST API specification
- Rule engine matching logic
- SBc-AP message coverage and encoding details
- PCAP export format
