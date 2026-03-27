"""Integration tests for the FastAPI app — no real SCTP needed."""
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

import sctp_probe.main as main_module
from sctp_probe.main import app


@pytest.fixture
async def reset_store():
    """Give each test an isolated in-memory store."""
    import sctp_probe.main as m
    from sctp_probe.store import Store
    new_store = Store(":memory:")
    await new_store.init_db()
    original = m._store
    m._store = new_store
    m._rule_engine._store = new_store
    yield new_store
    m._store = original
    m._rule_engine._store = original


@pytest.fixture
def mock_sctp(monkeypatch):
    srv = MagicMock()
    srv.start = AsyncMock()
    srv.stop = AsyncMock()
    srv.stop_all = AsyncMock()
    srv.send_to_peer = AsyncMock()
    srv.status = MagicMock(return_value=[])
    srv._listeners = {}

    cli = MagicMock()
    cli.connect = AsyncMock(return_value="conn-1")
    cli.disconnect = AsyncMock()
    cli.disconnect_all = AsyncMock()
    cli.send = AsyncMock()
    cli.status = MagicMock(return_value=[])
    cli._conns = {}

    monkeypatch.setattr(main_module, "_sctp_server", srv)
    monkeypatch.setattr(main_module, "_sctp_client", cli)
    return srv, cli


@pytest.fixture
async def client(reset_store, mock_sctp):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ------------------------------------------------------------------
# Server endpoints
# ------------------------------------------------------------------

async def test_server_status(client):
    r = await client.get("/api/server/status")
    assert r.status_code == 200
    assert "listeners" in r.json()


async def test_server_start(client, mock_sctp):
    srv, _ = mock_sctp
    r = await client.post("/api/server/start", json={"port": 29200, "ppid": 24})
    assert r.status_code == 200
    assert r.json()["status"] == "listening"
    srv.start.assert_called_once_with(29200, 24)


async def test_server_stop(client, mock_sctp):
    srv, _ = mock_sctp
    r = await client.post("/api/server/stop", json={"port": 29200})
    assert r.status_code == 200
    assert 29200 in r.json()["stopped"]


# ------------------------------------------------------------------
# Client endpoints
# ------------------------------------------------------------------

async def test_client_status(client):
    r = await client.get("/api/client/status")
    assert r.status_code == 200
    assert "connections" in r.json()


async def test_client_connect(client, mock_sctp):
    _, cli = mock_sctp
    r = await client.post("/api/client/connect", json={"host": "127.0.0.1", "port": 29200, "ppid": 24})
    assert r.status_code == 200
    assert r.json()["id"] == "conn-1"


# ------------------------------------------------------------------
# Rules endpoints
# ------------------------------------------------------------------

async def test_create_rule(client):
    r = await client.post("/api/rules", json={
        "match_pdu_type": "WRR_REQ",
        "action": "auto_reply",
        "reply_template": "WRR_SUCCESS",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["match_pdu_type"] == "WRR_REQ"
    assert data["id"] == 1


async def test_list_rules(client):
    await client.post("/api/rules", json={"match_pdu_type": "*", "action": "log_only"})
    r = await client.get("/api/rules")
    assert r.status_code == 200
    assert len(r.json()["rules"]) == 1


async def test_delete_rule(client):
    cr = await client.post("/api/rules", json={"match_pdu_type": "*", "action": "log_only"})
    rule_id = cr.json()["id"]
    r = await client.delete(f"/api/rules/{rule_id}")
    assert r.status_code == 200
    assert r.json()["deleted"] == 1


async def test_delete_all_rules(client):
    await client.post("/api/rules", json={"match_pdu_type": "*", "action": "log_only"})
    await client.post("/api/rules", json={"match_pdu_type": "SWR_REQ", "action": "drop"})
    r = await client.delete("/api/rules")
    assert r.status_code == 200
    assert r.json()["deleted"] == 2


# ------------------------------------------------------------------
# Messages endpoints
# ------------------------------------------------------------------

async def test_get_messages_empty(client):
    r = await client.get("/api/messages")
    assert r.status_code == 200
    assert r.json()["messages"] == []


async def test_get_messages_since_id(client):
    import sctp_probe.main as m
    # Save 3 messages directly via store
    for i in range(3):
        await m._store.save_message({
            "session_id": "s1", "timestamp": "2026-01-01T00:00:00+00:00",
            "direction": "inbound", "transport": "sctp",
            "protocol": "raw", "raw_hex": f"0{i}", "raw_bytes_b64": "",
        })
    r = await client.get("/api/messages?since_id=1")
    assert r.status_code == 200
    msgs = r.json()["messages"]
    assert len(msgs) == 2
    assert all(m["id"] > 1 for m in msgs)


async def test_delete_messages(client):
    import sctp_probe.main as m
    await m._store.save_message({
        "session_id": "s1", "timestamp": "2026-01-01T00:00:00+00:00",
        "direction": "inbound", "transport": "sctp",
        "protocol": "raw", "raw_hex": "00", "raw_bytes_b64": "",
    })
    r = await client.delete("/api/messages")
    assert r.status_code == 200
    assert r.json()["deleted"] == 1


# ------------------------------------------------------------------
# Session endpoint
# ------------------------------------------------------------------

async def test_session_reset(client):
    r = await client.post("/api/session/reset")
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data
    assert len(data["session_id"]) == 36  # UUID


async def test_session_reset_returns_new_id_each_time(client):
    r1 = await client.post("/api/session/reset")
    r2 = await client.post("/api/session/reset")
    assert r1.json()["session_id"] != r2.json()["session_id"]


# ------------------------------------------------------------------
# Export endpoints
# ------------------------------------------------------------------

async def test_export_json(client):
    r = await client.get("/api/export/json")
    assert r.status_code == 200


async def test_export_pcap_magic(client):
    r = await client.get("/api/export/pcap")
    assert r.status_code == 200
    assert r.content[:4] == b"\xd4\xc3\xb2\xa1"
