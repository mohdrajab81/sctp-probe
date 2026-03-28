# sctp-probe — Technical Design Document

Version: 1.0
Date: 2026-03-27
Status: Authoritative — all implementation must follow this document.

---

## 1. Purpose and Scope

sctp-probe is a standalone SCTP client/server testing tool with:

- A web UI for human-operated testing and real-time PDU inspection
- A REST API for automated test integration (CI, integration test suites)
- SBc-AP protocol decode/encode using pycrate
- An auto-reply rule engine for simulating MME/BSC responses
- A persistent message log (SQLite) for cross-session test assertions
- PCAP + JSON export for Wireshark-based independent verification

### Primary Use Cases

1. **MME simulator for SentinelCBC Phase 8.5** — Listen on SCTP port 29168, receive
   Write-Replace-Warning (WRR) and Stop-Warning (SWR) PDUs from SentinelCBC, auto-reply
   with configurable responses, confirm end-to-end dispatch over real SCTP.

2. **General SCTP transport testing** — Send and receive arbitrary binary payloads over
   SCTP without any protocol-specific logic. Useful for any SCTP-based protocol development.

3. **Automated integration test peer** — SentinelCBC integration tests configure sctp-probe
   via REST API before each test case, then assert on received PDUs after.

4. **Future protocol support** — CBSP (2G/GSM, TCP) and NR-CBC (5G) in later phases.
   The architecture must accommodate new protocol decoders/encoders without restructuring.

---

## 2. Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│  Browser / Automated Test Client                                │
│  (HTTP REST + WebSocket)                                        │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTP / WebSocket
┌────────────────────▼────────────────────────────────────────────┐
│  FastAPI Application (main.py)                                  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  REST API    │  │  WebSocket   │  │  Session Control     │  │
│  │  /api/*      │  │  /ws/events  │  │  /api/session/reset  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘  │
│         │                 │                                     │
│  ┌──────▼─────────────────▼────────────────────────────────┐   │
│  │  Core Services                                          │   │
│  │                                                         │   │
│  │  ┌────────────┐  ┌───────────┐  ┌────────────────────┐ │   │
│  │  │ RuleEngine │  │ Store     │  │ WsHub              │ │   │
│  │  │ rules.py   │  │ store.py  │  │ ws.py              │ │   │
│  │  └────────────┘  └───────────┘  └────────────────────┘ │   │
│  │                                                         │   │
│  │  ┌────────────┐  ┌───────────┐  ┌────────────────────┐ │   │
│  │  │ Decoder    │  │ Encoder   │  │ Exporter           │ │   │
│  │  │ decoder.py │  │ encoder.py│  │ export.py          │ │   │
│  │  └────────────┘  └───────────┘  └────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Transport Layer                                        │   │
│  │                                                         │   │
│  │  ┌──────────────────────┐  ┌───────────────────────┐   │   │
│  │  │ SctpServer           │  │ SctpClient            │   │   │
│  │  │ sctp_server.py       │  │ sctp_client.py        │   │   │
│  │  │ multi-listener       │  │ with heartbeat        │   │   │
│  │  └──────────────────────┘  └───────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                     │ SCTP / TCP
┌────────────────────▼────────────────────────────────────────────┐
│  Remote Peer (SentinelCBC, osmo-cbc, custom tool, etc.)        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

| Component | Choice | Reason |
| --- | --- | --- |
| Web framework | FastAPI (Python 3.11+) | Async WebSocket support, auto OpenAPI docs, pydantic validation |
| ASGI server | Uvicorn | Standard FastAPI runtime |
| SCTP library | pysctp (P1sec fork) | Linux kernel SCTP socket wrapper, same ecosystem as pycrate |
| Protocol decode/encode | pycrate 0.7.11 + compiled ASN.1 | pycrate 0.7.11 does not ship SBc-AP. 3GPP TS 29.168 V15.1.0 ASN.1 source files (from Wireshark) were compiled with `pycrate_asn1c` into `specs/SbcAP_gen.py`. |
| Persistence | SQLite (stdlib `sqlite3`) | Zero dependency, survives process restarts, sufficient for dev/test |
| Frontend | Vanilla HTML + JS (no framework, no build step) | Single file, no npm, instant load |
| WebSocket (browser) | Native browser WebSocket API | No library needed |
| PCAP export | stdlib `struct` | ~50 lines, no external dependency |

### SCTP Library Risk and Fallback

pysctp requires `libsctp-dev` and the Linux kernel SCTP module (`CONFIG_IP_SCTP`).
On WSL2 the default Microsoft kernel ships SCTP as a loadable module — run
`modprobe sctp` before starting. If pysctp cannot bind on the target environment,
the fallback is to run sctp-probe inside a Docker container (Linux kernel guaranteed).

Before implementing anything, verify pysctp works in the target environment:

```bash
# WSL2 Ubuntu
sudo apt install libsctp-dev lksctp-tools
sudo modprobe sctp
python -c "import sctp; print('pysctp OK')"
```

If this fails, switch to the Docker path. Document which path is in use in the README.

### pycrate SBc-AP Validation

Before using pycrate for decode in the tool, validate it against the existing SentinelCBC
fixture corpus at `C:\Projects\sentinel-cbc\schemas\protocol\fixtures\`.

Run each `.bin` file through pycrate's decoder and compare against the corresponding
`.expected.json`. Any mismatch means pycrate's SBc-AP decode is wrong for that IE — the
decoder module must handle the mismatch gracefully (log the raw hex, do not crash).

---

## 4. Data Model

### Message (stored in SQLite `messages` table)

```python
@dataclass
class Message:
    id: int                         # auto-increment primary key
    session_id: str                 # UUID, reset on POST /api/session/reset
    timestamp: str                  # ISO-8601 UTC
    direction: str                  # "inbound" | "outbound"
    transport: str                  # "sctp" | "tcp"
    local_port: int                 # listener port (server) or local port (client)
    peer_addr: str                  # remote IP:port
    protocol: str                   # "SBc-AP" | "CBSP" | "raw"
    pdu_type: str | None            # see section 5 for all PDU type keys
    message_identifier: str | None  # hex string e.g. "0x1144" or None
    serial_number: str | None       # hex string e.g. "0x0001" or None
    decoded: dict | None            # full decoded fields as dict, or None
    raw_hex: str                    # space-separated hex octets
    raw_bytes_b64: str              # base64 of raw bytes (for PCAP export)
    rule_id: int | None             # if outbound message was triggered by a rule
```

### Rule (stored in SQLite `rules` table)

```python
@dataclass
class Rule:
    id: int                               # auto-increment primary key
    active: bool                          # False = disabled, not deleted
    match_pdu_type: str                   # "WRR_REQ" | "SWR_REQ" | "*"
    match_message_identifier: str | None  # hex string or None (match any)
    match_serial_number: str | None       # hex string or None (match any)
    match_peer_addr: str | None           # "IP:port" or None (match any)
    action: str                           # "auto_reply" | "drop" | "log_only"
    reply_template: str | None            # see section 6 reply templates
    delay_ms: int                         # artificial delay before reply (0 = immediate)
    count: int                            # max replies (0 = unlimited)
    fired: int                            # how many times this rule has fired
```

### Session

No separate table. A session is identified by a UUID stored in memory.
`POST /api/session/reset` generates a new UUID, marks all existing messages as
belonging to the old session, and clears active rules. SCTP connections are not dropped.

---

## 5. SBc-AP Message Coverage

SentinelCBC implements the following SBc-AP message set (3GPP TS 29.168).
sctp-probe must decode all of them and encode all response and indication types
so it can act as a realistic MME peer.

### Messages Sent by SentinelCBC (CBC → MME Direction)

These arrive as inbound PDUs at sctp-probe when it acts as MME simulator.

| PDU type key | SBc-AP message | Notes |
| --- | --- | --- |
| `WRR_REQ` | Write-Replace-Warning-Request | Initiating message, APER |
| `SWR_REQ` | Stop-Warning-Request | Initiating message, APER |

### Messages Sent by MME (MME → CBC Direction)

These are produced by sctp-probe as replies or spontaneous indications.

| PDU type key | SBc-AP message | Notes |
| --- | --- | --- |
| `WRR_RESP` | Write-Replace-Warning-Response | Successful outcome |
| `SWR_RESP` | Stop-Warning-Response | Successful outcome |
| `ERR_IND` | Error-Indication | Async, unsolicited, initiating message |
| `WRWI` | Write-Replace-Warning-Indication | Async, cell feedback, initiating message |
| `SWI` | Stop-Warning-Indication | Async, cell feedback, initiating message |

### Deferred (not yet in SentinelCBC)

These are not produced by SentinelCBC yet but the decoder must recognise and log
them so sctp-probe can inject them for future testing.

| PDU type key | SBc-AP message | Notes |
| --- | --- | --- |
| `PWS_RESTART` | PWS-Restart-Indication | Deferred per SentinelCBC ADR-011 |
| `PWS_FAILURE` | PWS-Failure-Indication | Deferred per SentinelCBC ADR-011 |

---

## 6. Reply Templates

Each template produces a valid SBc-AP APER-encoded PDU.

### Response Templates (triggered by WRR_REQ or SWR_REQ)

MI and SN are echoed from the inbound request so SentinelCBC can correlate the response.

| Template name | PDU produced | Description |
| --- | --- | --- |
| `WRR_SUCCESS` | Write-Replace-Warning-Response | Cause = 0, no unknown TAIs |
| `WRR_PARTIAL` | Write-Replace-Warning-Response | Cause = 0, one synthetic unknown TAI |
| `WRR_PERMANENT_FAILURE` | Write-Replace-Warning-Response | Cause = permanent failure, RequiresRetry = false |
| `WRR_TRANSIENT_FAILURE` | Write-Replace-Warning-Response | Cause = transient failure, RequiresRetry = true |
| `WRR_TIMEOUT` | (no reply sent) | Rule fires but sends nothing — tests timeout handling |
| `SWR_SUCCESS` | Stop-Warning-Response | Cause = 0 |
| `SWR_NOT_FOUND` | Stop-Warning-Response | Cause = warning-not-found |

### Indication Templates (spontaneously sent or manually injected)

MI and SN are provided as input parameters — not echoed from a request.

| Template name | PDU produced | Description |
| --- | --- | --- |
| `ERR_IND_SEMANTIC` | Error-Indication | Cause = semantic-error |
| `ERR_IND_TRANSFER_SYNTAX` | Error-Indication | Cause = transfer-syntax-error |
| `WRWI_SCHEDULED` | Write-Replace-Warning-Indication | Broadcasts scheduled in some cells |
| `WRWI_CANCELLED` | Write-Replace-Warning-Indication | Broadcasts cancelled in some cells |
| `SWI_CANCELLED` | Stop-Warning-Indication | Stop confirmed in some cells |

Templates are defined in `encoder.py`. Adding a new template requires only a new
entry in the template registry — no changes to the rule engine or API.

---

## 7. Rule Engine

### Matching Logic

All conditions are ANDed. A `None` value means wildcard (match any).

```text
rule matches inbound message if:
  (rule.match_pdu_type == "*" OR rule.match_pdu_type == message.pdu_type)
  AND (rule.match_message_identifier is None
       OR rule.match_message_identifier == message.message_identifier)
  AND (rule.match_serial_number is None
       OR rule.match_serial_number == message.serial_number)
  AND (rule.match_peer_addr is None
       OR rule.match_peer_addr == message.peer_addr)
  AND (rule.count == 0 OR rule.fired < rule.count)
  AND rule.active == True
```

Rules are evaluated in insertion order (lowest id first). First matching rule wins.
If no rule matches, the message is logged and no reply is sent.

### Actions

- `auto_reply` — encode `reply_template`, apply `delay_ms`, send to the source peer
- `drop` — log the message but send no reply (simulates unresponsive peer)
- `log_only` — log only, no reply (explicit no-op rule for debugging)

---

## 8. REST API

Base URL: `http://localhost:{WEB_PORT}` (default `WEB_PORT=8765`)

All request/response bodies are JSON. All timestamps are ISO-8601 UTC.
Error responses follow RFC 7807.

### Server Management

```text
POST /api/server/start
Body:     { "port": 29168, "ppid": 24 }
          ppid: SCTP Payload Protocol Identifier (24 = SBc-AP per 3GPP TS 29.168)
Response: 200 { "port": 29168, "status": "listening" }
          409 already listening on that port

POST /api/server/stop
Body:     { "port": 29168 }   omit to stop all listeners
Response: 200 { "stopped": [29168] }

GET /api/server/status
Response: 200 { "listeners": [{ "port": 29168, "ppid": 24, "peers": ["127.0.0.1:54321"] }] }
```

### Client Management

```text
POST /api/client/connect
Body:     { "host": "127.0.0.1", "port": 29168, "ppid": 24 }
Response: 200 { "id": "conn-1", "status": "connected" }
          502 connection failed (error detail included)

POST /api/client/disconnect
Body:     { "id": "conn-1" }   omit to disconnect all
Response: 200 { "disconnected": ["conn-1"] }

GET /api/client/status
Response: 200 { "connections": [{ "id": "conn-1", "host": "127.0.0.1",
                                  "port": 29168, "state": "CONNECTED" }] }
```

### Rules

```text
POST /api/rules
Body: {
  "match_pdu_type": "WRR_REQ",          required: "WRR_REQ"|"SWR_REQ"|"*"
  "match_message_identifier": null,     optional hex string e.g. "0x1144"
  "match_serial_number": null,          optional hex string e.g. "0x0001"
  "match_peer_addr": null,              optional "IP:port"
  "action": "auto_reply",               required: "auto_reply"|"drop"|"log_only"
  "reply_template": "WRR_SUCCESS",      required when action = "auto_reply"
  "delay_ms": 0,                        optional, default 0
  "count": 0                            optional, default 0 (unlimited)
}
Response: 201 { "id": 1, ...rule fields... }

GET    /api/rules           Response: 200 { "rules": [...] }
DELETE /api/rules/{id}      Response: 200 { "deleted": 1 }
DELETE /api/rules           Response: 200 { "deleted": N }
```

### Messages

```text
GET /api/messages
Query params:
  since_id=N          only return messages with id > N (default 0 = all)
  direction=inbound   filter by direction
  pdu_type=WRR_REQ    filter by pdu_type
  limit=100           max results (default 100, max 1000)
Response: 200 { "messages": [...], "total": N }

DELETE /api/messages   Response: 200 { "deleted": N }
```

### Manual Send

```text
POST /api/send
Body: {
  "hex": "00 20 00 05 ...",       space or no-space hex string
  "connection_id": "conn-1",      client connection id, or omit for server broadcast
  "template": "ERR_IND_SEMANTIC", alternative to hex — use a named template
  "message_identifier": "0x1144", required when using indication templates
  "serial_number": "0x0001"       required when using indication templates
}
Response: 200 { "sent_bytes": N }
          400 malformed hex or missing required field
          409 not connected
```

### Session

```text
POST /api/session/reset
Response: 200 { "session_id": "new-uuid", "cleared_messages": N, "cleared_rules": N }
```

### Export

```text
GET /api/export/json
Query params: session_id=...   default: current session
Response: 200 application/json

GET /api/export/pcap
Query params: session_id=...   default: current session
Response: 200 application/vnd.tcpdump.pcap
```

### WebSocket

```text
WS /ws/events
Pushes JSON events to connected browsers:

{ "type": "message",     "data": { ...message object... } }
{ "type": "connection",  "data": { "event": "assoc_up"|"assoc_down",
                                   "peer": "IP:port", "port": 29168 } }
{ "type": "rule_fired",  "data": { "rule_id": 1, "message_id": 42 } }
```

---

## 9. Web UI

Single file: `static/index.html`. No build step. No npm. No external CDN dependencies.

### Three-Panel Layout

```text
┌─────────────────────────────────────────────────────────────────────┐
│  sctp-probe v0.1                                    [Docs] [GitHub] │
├──────────────────┬──────────────────────────────┬───────────────────┤
│ CONNECTIONS      │ MESSAGE LOG                  │ COMPOSE & RULES   │
│                  │                              │                   │
│ -- Server --     │ [Clear] [Export JSON] [PCAP] │ -- Send raw --    │
│ Port: [29168]    │                              │ Hex input box     │
│ PPID: [24   ]    │ 10:04:01 <- ASSOC            │ [Send]            │
│ [Start] [Stop]   │   127.0.0.1:54321            │                   │
│                  │                              │ -- Auto-reply --  │
│ Listeners:       │ 10:04:02 <- WRR_REQ          │ PDU:  [WRR_REQ v] │
│ * :29168  [x]    │   MI: 0x1144  SN: 0x0001    │ MI:   [any     ]  │
│                  │   Family: EU_ALERT           │ SN:   [any     ]  │
│ -- Client --     │   Area: TAI_LIST             │ Peer: [any     ]  │
│ Host: [       ]  │   [> raw hex]               │                   │
│ Port: [29168  ]  │                              │ Action: [auto  v] │
│ [Connect]        │ 10:04:02 -> WRR_SUCCESS      │ Tmpl:  [SUCCESS v]│
│                  │   Cause: 0 (success)         │ Delay: [0   ] ms  │
│ Connections:     │   [> raw hex]               │ Count: [0      ]  │
│ (none)           │                              │ [Add rule]        │
│                  │ 10:04:03 <- WRWI             │                   │
│                  │   MI: 0x1144  SN: 0x0001    │ Active rules:     │
│                  │   Scheduled: 3 cells         │ #1 WRR_REQ->      │
│                  │                              │    SUCCESS [x]    │
│                  │ 10:04:04 <- SWI              │                   │
│                  │   MI: 0x1144  SN: 0x0001    │                   │
│                  │   Cancelled: 3 cells         │                   │
└──────────────────┴──────────────────────────────┴───────────────────┘
```

### UI Behaviours

- Message log shows all PDU types: WRR_REQ, SWR_REQ, WRR_RESP, SWR_RESP,
  ERR_IND, WRWI, SWI, PWS_RESTART, PWS_FAILURE, and raw unknown.
- Each entry is expandable to show full decoded fields and raw hex.
- Live updates via WebSocket — reconnects with 2-second backoff on disconnect.
  Header shows "LIVE" / "RECONNECTING" badge.
- Connection badges: green = connected/listening, red = disconnected/error.
- Export buttons trigger `GET /api/export/json` and `GET /api/export/pcap` downloads.
- Rules list shows active rules with fired count and a delete button.
- Three panels stack vertically on narrow screens (< 900px).

---

## 10. Module Responsibilities

### `main.py`

- FastAPI app instantiation and lifespan handler
- Startup: init SQLite, create tables
- Shutdown: close all SCTP sockets
- Router registration
- Static file serving for `static/index.html`
- Environment variable loading (`WEB_PORT`, `DB_PATH`, `LOG_LEVEL`)
- Wires callbacks: `sctp_server.on_message` → decode → store → ws_hub → rule_engine

### `sctp_server.py`

- `SctpServer` class managing `{port: listening_socket}`
- `start(port, ppid)` — bind, spawn accept loop as asyncio task
- `stop(port)` — close socket, cancel task
- `accept_loop(port)` — accept associations, spawn `handle_conn` per peer
- `handle_conn(conn, peer_addr, port)` — read loop, calls `on_message` callback
- `send_to_peer(peer_addr, raw_bytes)` — send reply to a specific peer
- All socket operations on asyncio event loop; no threading

### `sctp_client.py`

- `SctpClient` class managing `{conn_id: {socket, peer_addr, state, read_task}}`
- `connect(host, port, ppid)` — open association, spawn read loop, return conn_id
- `disconnect(conn_id)` — close socket, cancel read loop
- `send(conn_id, raw_bytes)` — write to socket
- `heartbeat_loop(conn_id)` — periodic liveness check, updates state on failure
- Read loop calls same `on_message` callback as server

### `decoder.py`

- `decode(raw_bytes: bytes) -> DecodedMessage`
- `peek_pdu_type(raw_bytes: bytes) -> str | None`
- `DecodedMessage` dataclass covering all fields in section 4
- Decodes all PDU types in section 5 including async indications:
  ERR_IND, WRWI, SWI, PWS_RESTART, PWS_FAILURE
- Never raises — all exceptions caught, fallback to `protocol="raw"`, `pdu_type=None`

### `encoder.py`

- `encode(template_name: str, inbound: DecodedMessage | None, **kwargs) -> bytes | None`
- `inbound` used to echo MI/SN for response templates
- `kwargs` used to supply MI/SN for indication templates (not triggered by a request)
- Template registry dict — all templates from section 6
- Never raises — returns `None` on failure with error logged

### `rules.py`

- `RuleEngine` holding references to `store`, `encoder`, `sctp_server`, `sctp_client`
- `evaluate(inbound_msg, source_conn)` — find first matching rule, execute action
- `_match(rule, msg) -> bool` — pure function, no I/O
- `_execute(rule, msg, conn)` — apply delay, encode, send, increment fired count

### `store.py`

- SQLite via stdlib `sqlite3`, wrapped in `asyncio.to_thread`
- Tables: `messages`, `rules`, `meta` (stores current session_id)
- All methods async — never block the event loop directly
- Full method list: `save_message`, `get_messages`, `save_rule`, `get_rules`,
  `delete_rule`, `delete_all_rules`, `reset_session`, `delete_all_messages`

### `ws.py`

- `WsHub` with `connect(ws)`, `disconnect(ws)`, `broadcast(event_dict)`
- `broadcast` catches and ignores `WebSocketDisconnect` per subscriber
- No dependencies on transport or storage

### `export.py`

- `export_json(store, session_id) -> str`
- `export_pcap(store, session_id) -> bytes` — see section 12 for format
- Both handle empty message log gracefully

### `session.py`

- `reset(store) -> dict` — calls `store.reset_session()`, returns summary

---

## 11. Configuration (Environment Variables)

| Variable | Default | Description |
| --- | --- | --- |
| `WEB_PORT` | `8765` | Port the FastAPI HTTP server listens on |
| `DB_PATH` | `sctp_probe.db` | SQLite file path. Use `:memory:` for ephemeral mode |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `AUTO_MODPROBE` | `false` | If `true`, run `modprobe sctp` on startup (needs sudo) |

---

## 12. PCAP Export Format

The PCAP file is minimal but Wireshark-compatible.

```text
Global header (24 bytes):
  magic_number:  0xa1b2c3d4  little-endian
  version_major: 2
  version_minor: 4
  thiszone:      0
  sigfigs:       0
  snaplen:       65535
  network:       1  (LINKTYPE_ETHERNET)

Per-message record:
  ts_sec:   Unix timestamp seconds
  ts_usec:  microseconds
  incl_len: len(frame)
  orig_len: len(frame)
  data:     Ethernet(14B) + IPv4(20B) + SCTP common header(12B)
            + SCTP DATA chunk(16B) + SBc-AP payload
```

Each message is wrapped in a full synthetic protocol stack so Wireshark
dissects the complete Ethernet/IPv4/SCTP/SBc-AP hierarchy without any
manual "Decode As" step.

Fake addresses used for all packets:

- Inbound (peer → probe): src=10.0.0.2:29168  dst=127.0.0.1:29168
- Outbound (probe → peer): src=127.0.0.1:29168  dst=10.0.0.2:29168

The IPv4 checksum is computed correctly. The SCTP checksum is set to 0
(Wireshark accepts this with checksum validation disabled, which is the
default for lab captures). The SBc-AP PPID (24) is set in the SCTP DATA
chunk header so Wireshark auto-selects the SBc-AP dissector.

---

## 13. Testing Strategy

Testing is split across two cooperating repos:

- `sctp-probe` covers the simulator itself via pytest.
- `sentinel-cbc` covers CBC application behavior via Go unit tests, internal
  integration tests, and live external SCTP integration against `sctp-probe`.

### 13.1 Current Inventory Snapshot (2026-03-28)

| Repo | Category | Count | Notes |
| --- | --- | ---: | --- |
| `sctp-probe` | Unit/component pytest | 43 | Store, decoder, encoder, rule matching |
| `sctp-probe` | In-process integration pytest | 29 | FastAPI endpoints, rule flow, Phase 11 regression |
| `sctp-probe` | SCTP/Linux-only pytest | 3 | Real SCTP socket smoke tests |
| `sctp-probe` | Live external-system pytest | 7 | Requires live `sctp-probe`, `sentinel-cbc`, and Postgres |
| `sctp-probe` | Other test utility | 1 | `validate_fixtures.py` CLI, not a pytest module |
| `sentinel-cbc` | Unit/component Go tests | 135 | API, service, delivery, protocol, store, config, metrics |
| `sentinel-cbc` | Internal integration Go tests | 81 | Real app-stack and PostgreSQL-backed integration |
| `sentinel-cbc` | Live external Go tests | 34 top-level / 49 concrete cases | Real `sentinel-cbc` to `sctp-probe` to Postgres verification |

### 13.2 `sctp-probe` Test Groups

```text
tests/
  test_store.py              unit/component: SQLite store operations
  test_decoder.py            unit/component: decode safety + fixture-backed decode checks
  test_encoder.py            unit/component: reply template encode + round-trip decode
  test_rules.py              mixed: unit matching tests + rule-evaluation integration tests
  test_api.py                in-process integration: FastAPI app, mocked SCTP
  test_phase11.py            in-process integration: Phase 11 regression coverage
  test_sctp_transport.py     SCTP transport smoke tests, @pytest.mark.sctp, Linux/WSL2 only
  test_integration_phase11.py live external integration, @pytest.mark.integration
  validate_fixtures.py       CLI: cross-validate against sentinel-cbc fixture corpus
```

### 13.3 `sentinel-cbc` Test Groups Relevant to This Tool

- Unit/component tests verify API handlers, services, delivery logic, codecs,
  config, metrics, and stores.
- Internal integration tests wire the CBC HTTP stack to a real PostgreSQL
  backend and, for worker-oriented slices, to fake transport doubles.
- Live external integration in `tests/integration/live_sctp_probe_test.go`
  verifies the real CBC to simulator path over HTTP, Postgres, and SCTP.

The live external CBC suite currently expands into 49 concrete cases grouped as:

| Live Suite | Count | Coverage |
| --- | ---: | --- |
| Single-peer full live suite | 33 | Happy path, response matrix, warning families, delivery areas, validation, async correlation, duplicate handling, discard paths |
| Multi-peer live suite | 3 | Fan-out and mixed per-peer outcomes |
| Multi-instance live suite | 5 | No duplicate sends, cross-instance stop, restart behavior, failover, stale reservation reclaim |
| Timing / retry / failure suite | 8 | Delayed responses, retries, terminal timeout, transport failure, stop equivalents |

### 13.4 Environment Matrix

| Test Category | Windows | WSL2/Linux | Notes |
| --- | --- | --- | --- |
| `sctp-probe` unit/component pytest | Yes | Yes | Some cases still depend on optional pycrate and fixture availability |
| `sctp-probe` in-process integration pytest | Yes | Yes | No real SCTP required |
| `sctp-probe` SCTP smoke tests | No | Yes | Requires Linux SCTP kernel support and `pysctp` |
| `sctp-probe` live Phase 11 pytest | No practical support | Yes | Requires live `sctp-probe`, `sentinel-cbc`, and Postgres in the same WSL2 environment |
| `sentinel-cbc` unit/component Go tests | Yes | Yes | Standard Go test execution |
| `sentinel-cbc` internal integration Go tests | Yes | Yes | Uses Testcontainers by default or `SENTINEL_TEST_DSN` local fast-path |
| `sentinel-cbc` live external Go tests | No practical support | Yes | Requires live SCTP path against `sctp-probe` |

### 13.5 Skip Behavior and Optional Dependencies

- `@pytest.mark.sctp` tests skip automatically when `pysctp` or Linux SCTP
  kernel support is unavailable.
- Encoder tests skip when the pycrate SBc-AP runtime is unavailable.
- Decoder fixture-specific tests skip when the SentinelCBC fixture corpus is not
  present at the configured path.
- `@pytest.mark.integration` tests skip when live `sctp-probe`,
  `sentinel-cbc`, or Postgres endpoints are not reachable.
- The CBC live Go suite also self-skips when required probe, CBC, or Postgres
  endpoints are unavailable.

### 13.6 Documentation Boundaries

- Keep exact day-to-day run commands in `README.md`.
- Keep the detailed CBC live-suite case catalog in
  `sentinel-cbc/tests/integration/README.md`.
- Keep per-run evidence in `artifacts/*/manifest.txt`, exported JSON, and PCAP
  captures.
- Keep this design document at the taxonomy, architecture, and environment-rule
  level so it remains authoritative without becoming a volatile test ledger.

---

## 14. Known Limitations and Deferred Scope

| Item | Status | Notes |
| --- | --- | --- |
| CBSP (2G/TCP) | Deferred — Phase 10 | Add `decoder_cbsp.py` + `encoder_cbsp.py` |
| NR-CBC (5G) | Deferred — Phase 10 | Same pattern as SBc-AP |
| PWS-Restart-Indication decode | Implemented — log only | Not produced by SentinelCBC yet |
| PWS-Failure-Indication decode | Implemented — log only | Not produced by SentinelCBC yet |
| SCTP multi-homing | Deferred | pysctp supports it; add later |
| TLS over SCTP | Not planned | Lab/test tool, not exposed publicly |
| Auth on web UI | Not planned | Local dev/lab use only |
| Full SCTP-framed PCAP | Implemented | Ethernet/IPv4/SCTP/SBc-AP stack, Wireshark auto-dissects |
