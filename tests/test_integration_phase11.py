"""Full Phase 11 live integration test — self-contained setup.

What this test does (mirrors the Phase 11 task list exactly):

  Step 1  — Verify docker infra (postgres + redis) is running; start if containers exist
             but are stopped.  Skip if docker is unavailable.
  Step 2  — Seed the sctp-probe-mme peer row into Postgres (upsert, safe to re-run).
  Step 3  — sctp-probe must already be running (http://127.0.0.1:8765).
             The test does NOT start uvicorn — that requires a separate terminal.
  Step 4  — Start the SCTP listener on port 29168 and add the WRR_SUCCESS auto-reply rule.
  Step 5  — SentinelCBC must already be running (http://127.0.0.1:8080).
             The test does NOT start 'go run' — that requires a separate terminal.
             It waits up to 15 s for SentinelCBC to connect to sctp-probe
             (evidence: /api/server/status shows a peer for port 29168).
  Step 6  — POST the warning to SentinelCBC.
  Step 7  — Poll sctp-probe for inbound WRR_REQ with protocol=SBc-AP.
  Step 8  — Poll sctp-probe for outbound WRR_RESP with matching MI+SN.
  Step 9  — Query Postgres: warning_peer_dispatches.state = DONE.
  Step 10 — Export PCAP to /tmp/phase11.pcap and copy to Windows Desktop.
             Verify PCAP magic bytes and non-empty packet records.

Run with:
    pytest tests/test_integration_phase11.py -v -m integration -s

Skipped automatically when sctp-probe or SentinelCBC are not running.
"""
from __future__ import annotations

import subprocess
import time
import pytest
import httpx

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROBE_URL       = "http://127.0.0.1:8765"
SENTINEL_URL    = "http://127.0.0.1:8080"
POSTGRES_DSN    = "postgres://sentinelcbc:sentinelcbc@127.0.0.1:5432/sentinel_cbc?sslmode=disable"
SCTP_PORT       = 29168
PEER_ID         = "sctp-probe-mme"
PCAP_WSL_PATH   = "/tmp/phase11_integration.pcap"
PCAP_WIN_PATH   = "/mnt/c/Users/DELL/OneDrive/Desktop/phase11_integration.pcap"

DOCKER_COMPOSE  = [
    "docker", "compose",
    "-f", "/mnt/c/Projects/sentinel-cbc/deployments/docker/docker-compose.yaml",
]

WARNING_PAYLOAD = {
    "family": "CMAS",
    "cmasCategory": "PRESIDENTIAL",
    "urgency": "IMMEDIATE",
    "certainty": "OBSERVED",
    "language": "en",
    "messageText": "Phase 11 integration test",
    "targetScope": "SPECIFIC_AREA",
    "deliveryArea": {
        "type": "TAI_LIST",
        "taiList": [{"plmn": "41601", "tacHex": "0001"}],
    },
    "broadcastBehavior": "BROADCAST_ONCE",
    "targetPeerIds": [PEER_ID],
}

SEED_PEER_SQL = """
INSERT INTO peers (id, name, primary_address, secondary_address, enabled,
                   connection_state, association_id, inbound_streams, outbound_streams,
                   last_connected_at, last_disconnected_at, updated_at)
VALUES ('sctp-probe-mme', 'sctp-probe MME simulator', '127.0.0.1', '',
        true, 'DISCONNECTED', NULL, NULL, NULL, NULL, NULL, now())
ON CONFLICT (id) DO UPDATE
  SET primary_address = EXCLUDED.primary_address,
      enabled         = EXCLUDED.enabled,
      updated_at      = now();
"""


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _run(cmd: list[str], timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _psql(sql: str, extra_flags: list[str] | None = None) -> subprocess.CompletedProcess:
    flags = extra_flags or []
    return _run(["psql", POSTGRES_DSN] + flags + ["-c", sql])


def _probe_get(path: str, **params) -> dict:
    with httpx.Client(base_url=PROBE_URL, timeout=10) as c:
        return c.get(path, params=params).json()


# ---------------------------------------------------------------------------
# Step 1 — Docker infrastructure
# ---------------------------------------------------------------------------

def _ensure_docker_infra():
    """Ensure postgres and redis containers are running.

    If docker is not available, skip rather than fail — the user may be
    running the DBs natively.
    """
    check = _run(["docker", "info"])
    if check.returncode != 0:
        # docker not available — assume user has infra running natively
        return

    up = _run(DOCKER_COMPOSE + ["up", "-d", "postgres", "redis"])
    assert up.returncode == 0, (
        f"docker compose up failed:\n{up.stdout}\n{up.stderr}"
    )

    # Give containers a moment to become healthy
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        ps = _run(DOCKER_COMPOSE + ["ps", "--format", "json"])
        if "running" in ps.stdout.lower() or "healthy" in ps.stdout.lower():
            break
        time.sleep(1)


# ---------------------------------------------------------------------------
# Step 2 — Seed peer
# ---------------------------------------------------------------------------

def _seed_peer():
    result = _psql(SEED_PEER_SQL)
    assert result.returncode == 0, (
        f"Peer seed failed:\n{result.stdout}\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# Step 4 — sctp-probe listener + rule
# ---------------------------------------------------------------------------

def _reset_probe():
    with httpx.Client(base_url=PROBE_URL, timeout=10) as c:
        c.delete("/api/messages")
        c.delete("/api/rules")
        c.post("/api/session/reset")


def _start_listener_and_rule():
    with httpx.Client(base_url=PROBE_URL, timeout=10) as c:
        r = c.post("/api/server/start", json={"port": SCTP_PORT, "ppid": 24})
        assert r.status_code in (200, 409), f"server/start: {r.status_code} {r.text}"

        r = c.post("/api/rules", json={
            "match_pdu_type": "WRR_REQ",
            "action": "auto_reply",
            "reply_template": "WRR_SUCCESS",
            "count": 0,
        })
        assert r.status_code == 201, f"POST /api/rules: {r.status_code} {r.text}"


# ---------------------------------------------------------------------------
# Step 5 — wait for SentinelCBC peer connection
# ---------------------------------------------------------------------------

def _wait_for_peer_connected(timeout_s: float = 15.0) -> bool:
    """Poll /api/server/status until port 29168 has at least one connected peer."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            status = _probe_get("/api/server/status")
            for listener in status.get("listeners", []):
                if listener.get("port") == SCTP_PORT:
                    if listener.get("peers"):
                        return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


# ---------------------------------------------------------------------------
# Step 6 — post warning
# ---------------------------------------------------------------------------

def _post_warning() -> dict:
    with httpx.Client(base_url=SENTINEL_URL, timeout=10) as c:
        r = c.post("/api/v1/warnings", json=WARNING_PAYLOAD)
        assert r.status_code in (200, 201, 202), (
            f"POST /api/v1/warnings: {r.status_code} {r.text}"
        )
        return r.json()


# ---------------------------------------------------------------------------
# Poll helpers
# ---------------------------------------------------------------------------

def _poll_message(
    pdu_type: str,
    direction: str,
    timeout_s: float = 12.0,
) -> dict | None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        msgs = _probe_get("/api/messages", limit=100).get("messages", [])
        for m in msgs:
            if m.get("pdu_type") == pdu_type and m.get("direction") == direction:
                return m
        time.sleep(0.5)
    return None


def _get_dispatch_state() -> str | None:
    sql = (
        "SELECT state FROM warning_peer_dispatches "
        f"WHERE peer_id = '{PEER_ID}' ORDER BY id DESC LIMIT 1;"
    )
    result = _psql(sql, extra_flags=["-t", "-A"])
    if result.returncode == 0:
        return result.stdout.strip() or None
    return None


# ---------------------------------------------------------------------------
# Module-scoped fixture — runs all setup once for the whole test file
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def phase11_setup():
    """Full Phase 11 setup: infra → seed → reset probe → listener/rule → sentinel check."""
    # Check sctp-probe is up
    try:
        r = httpx.get(f"{PROBE_URL}/api/server/status", timeout=3)
        assert r.status_code < 500
    except Exception:
        pytest.skip(f"sctp-probe not running at {PROBE_URL}")

    # Check SentinelCBC is up
    try:
        httpx.get(f"{SENTINEL_URL}/api/v1/warnings", timeout=3)
        # any response (even 405) means it's up
    except Exception:
        pytest.skip(f"SentinelCBC not running at {SENTINEL_URL}")

    # Step 1 — docker infra
    _ensure_docker_infra()

    # Step 2 — seed peer (safe upsert)
    _seed_peer()

    # Step 4 — reset probe, start listener, add rule
    _reset_probe()
    _start_listener_and_rule()

    # Step 5 — wait for SentinelCBC to connect (it dials at startup)
    connected = _wait_for_peer_connected(timeout_s=15)
    if not connected:
        pytest.skip(
            "SentinelCBC did not connect to sctp-probe within 15 s — "
            "ensure SENTINELCBC_SCTP_ENABLED=true and restart SentinelCBC after seeding the peer"
        )

    # Step 6 — trigger the warning
    _post_warning()


# ---------------------------------------------------------------------------
# Step 7 — inbound WRR_REQ received and decoded
# ---------------------------------------------------------------------------

def test_wrr_req_received():
    """sctp-probe must log an inbound WRR_REQ with protocol=SBc-AP."""
    msg = _poll_message("WRR_REQ", "inbound", timeout_s=12)
    assert msg is not None, "sctp-probe did not receive WRR_REQ within 12 s"
    assert msg["protocol"] == "SBc-AP", (
        f"protocol={msg['protocol']!r} — pycrate decode fell back to raw"
    )
    assert msg["message_identifier"] is not None, "message_identifier is None"
    assert msg["serial_number"] is not None, "serial_number is None"


# ---------------------------------------------------------------------------
# Step 8 — outbound WRR_RESP logged with matching MI+SN
# ---------------------------------------------------------------------------

def test_wrr_resp_sent():
    """sctp-probe must log an outbound WRR_RESP."""
    msg = _poll_message("WRR_RESP", "outbound", timeout_s=12)
    assert msg is not None, "sctp-probe did not log outbound WRR_RESP within 12 s"
    assert msg["protocol"] == "SBc-AP"
    assert msg["peer_addr"] is not None


def test_mi_sn_echoed():
    """WRR_RESP must echo the same Message-Identifier and Serial-Number as WRR_REQ."""
    msgs = _probe_get("/api/messages", limit=100).get("messages", [])
    req = next((m for m in msgs if m.get("pdu_type") == "WRR_REQ"
                and m.get("direction") == "inbound"), None)
    resp = next((m for m in msgs if m.get("pdu_type") == "WRR_RESP"
                 and m.get("direction") == "outbound"), None)

    assert req is not None, "No inbound WRR_REQ in message log"
    assert resp is not None, "No outbound WRR_RESP in message log"

    assert resp["message_identifier"] == req["message_identifier"], (
        f"MI mismatch — req={req['message_identifier']} resp={resp['message_identifier']}"
    )
    assert resp["serial_number"] == req["serial_number"], (
        f"SN mismatch — req={req['serial_number']} resp={resp['serial_number']}"
    )


def test_no_raw_fallback():
    """All messages must have protocol=SBc-AP, not protocol=raw."""
    msgs = _probe_get("/api/messages", limit=100).get("messages", [])
    raw = [m for m in msgs if m.get("protocol") == "raw"]
    assert not raw, (
        f"{len(raw)} message(s) with protocol=raw: "
        f"{[m.get('pdu_type') for m in raw]}"
    )


# ---------------------------------------------------------------------------
# Step 9 — Postgres dispatch state = DONE
# ---------------------------------------------------------------------------

def test_dispatch_state_done():
    """Postgres warning_peer_dispatches.state must be DONE."""
    # Poll a few times — SentinelCBC processes the reply asynchronously
    deadline = time.monotonic() + 10
    state = None
    while time.monotonic() < deadline:
        state = _get_dispatch_state()
        if state == "DONE":
            break
        time.sleep(0.5)

    assert state is not None, (
        f"No dispatch row found for peer_id={PEER_ID!r}"
    )
    assert state == "DONE", f"Expected state=DONE, got {state!r}"


# ---------------------------------------------------------------------------
# Step 10 — PCAP export
# ---------------------------------------------------------------------------

def test_pcap_export_magic_bytes():
    """GET /api/export/pcap must return a valid PCAP file."""
    with httpx.Client(base_url=PROBE_URL, timeout=10) as c:
        r = c.get("/api/export/pcap")
    assert r.status_code == 200, f"PCAP export: {r.status_code}"
    assert r.headers.get("content-type", "").startswith("application/vnd.tcpdump.pcap")
    assert r.content[:4] in (b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4"), (
        f"Bad PCAP magic: {r.content[:4].hex()}"
    )
    assert len(r.content) > 24, "PCAP has no packet records (file too short)"


def test_pcap_written_to_desktop():
    """PCAP must be saved to /tmp and copied to the Windows Desktop."""
    with httpx.Client(base_url=PROBE_URL, timeout=10) as c:
        data = c.get("/api/export/pcap").content

    with open(PCAP_WSL_PATH, "wb") as f:
        f.write(data)

    result = _run(["cp", PCAP_WSL_PATH, PCAP_WIN_PATH])
    assert result.returncode == 0, (
        f"cp to Desktop failed: {result.stderr}"
    )

    import os
    size = os.path.getsize(PCAP_WSL_PATH)
    assert size > 24, f"PCAP on disk is too small ({size} bytes)"
    print(f"\nPCAP written: {PCAP_WIN_PATH} ({size} bytes)")
    print("Open in Wireshark — verify Write-Replace-Warning-Request with correct MI in SBc-AP tree.")
