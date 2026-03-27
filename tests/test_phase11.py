"""Phase 11 regression tests — covers the three bugs found during SentinelCBC
integration and the full WRR_REQ → WRR_SUCCESS pipeline.

All tests run without real SCTP or pycrate (mocked where needed).
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sctp_probe.rules import RuleEngine
from sctp_probe.store import Store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _msg(**kwargs):
    base = {
        "id": 1,
        "session_id": "s1",
        "direction": "inbound",
        "transport": "sctp",
        "local_port": 29168,
        "peer_addr": "127.0.0.1:54321",
        "pdu_type": "WRR_REQ",
        "message_identifier": "0x1144",
        "serial_number": "0x0001",
        "protocol": "SBc-AP",
        "decoded": {},
        "raw_hex": "deadbeef",
        "raw_bytes_b64": "",
    }
    base.update(kwargs)
    return base


def _make_decoder(pdu_type="WRR_RESP"):
    """Return a minimal mock decoder whose decode() returns a DecodedMessage-like object."""
    from sctp_probe.decoder import DecodedMessage
    dm = DecodedMessage(
        protocol="SBc-AP",
        pdu_type=pdu_type,
        message_identifier="0x1144",
        serial_number="0x0001",
        decoded={},
        raw_hex="aabbcc",
        raw_bytes_b64="",
    )
    mock_dec = MagicMock()
    mock_dec.decode = MagicMock(return_value=dm)
    return mock_dec


# ---------------------------------------------------------------------------
# Bug 2 — store.py: bytes values in decoded dict must round-trip through JSON
# ---------------------------------------------------------------------------

async def test_store_save_message_bytes_in_decoded(store):
    """store.save_message must not raise when decoded contains bytes values."""
    msg = {
        "session_id": "s1",
        "timestamp": "2026-03-27T00:00:00+00:00",
        "direction": "inbound",
        "transport": "sctp",
        "local_port": 29168,
        "peer_addr": "127.0.0.1:54321",
        "protocol": "SBc-AP",
        "pdu_type": "WRR_REQ",
        "message_identifier": "0x1144",
        "serial_number": "0x0001",
        "decoded": {"Warning-Message-Content": b"\xde\xad\xbe\xef"},
        "raw_hex": "deadbeef",
        "raw_bytes_b64": "",
    }
    saved = await store.save_message(msg)
    assert saved["id"] >= 1
    # The decoded column must be stored without raising — verify it round-trips
    msgs = await store.get_messages()
    assert any(m["id"] == saved["id"] for m in msgs)


async def test_store_decoded_bytes_serialised_as_hex(store):
    """bytes values inside decoded must come back as hex strings, not crash."""
    msg = {
        "session_id": "s1",
        "timestamp": "2026-03-27T00:00:00+00:00",
        "direction": "inbound",
        "transport": "sctp",
        "local_port": 29168,
        "peer_addr": "127.0.0.1:54321",
        "protocol": "SBc-AP",
        "pdu_type": "WRR_REQ",
        "message_identifier": "0x1144",
        "serial_number": "0x0001",
        "decoded": {"payload": b"\x00\x01\x02\x03"},
        "raw_hex": "00010203",
        "raw_bytes_b64": "",
    }
    saved = await store.save_message(msg)
    msgs = await store.get_messages()
    row = next(m for m in msgs if m["id"] == saved["id"])
    # decoded is stored as JSON; bytes must have been serialised to hex
    decoded = row["decoded"]
    if isinstance(decoded, str):
        decoded = json.loads(decoded)
    assert decoded["payload"] == "00010203"


# ---------------------------------------------------------------------------
# Bug 3 — rules.py: outbound reply must be logged and broadcast
# ---------------------------------------------------------------------------

async def test_auto_reply_logs_outbound_message():
    """After auto_reply fires, the outbound message must be saved to the store."""
    store = Store(":memory:")
    await store.init_db()

    mock_enc = MagicMock()
    mock_enc.encode = MagicMock(return_value=b"\xaa\xbb\xcc")

    mock_srv = MagicMock()
    mock_srv.send_to_peer = AsyncMock()

    mock_dec = _make_decoder("WRR_RESP")

    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()

    engine = RuleEngine(store, mock_enc, mock_srv, None,
                        decoder=mock_dec, ws_hub=mock_ws)

    await store.save_rule({
        "match_pdu_type": "WRR_REQ",
        "action": "auto_reply",
        "reply_template": "WRR_SUCCESS",
    })

    await engine.evaluate(_msg(), None)

    msgs = await store.get_messages()
    outbound = [m for m in msgs if m["direction"] == "outbound"]
    assert len(outbound) == 1
    assert outbound[0]["pdu_type"] == "WRR_RESP"
    assert outbound[0]["peer_addr"] == "127.0.0.1:54321"


async def test_auto_reply_broadcasts_via_ws_hub():
    """After auto_reply, ws_hub.broadcast must be called at least once."""
    store = Store(":memory:")
    await store.init_db()

    mock_enc = MagicMock()
    mock_enc.encode = MagicMock(return_value=b"\xaa\xbb\xcc")

    mock_srv = MagicMock()
    mock_srv.send_to_peer = AsyncMock()

    mock_dec = _make_decoder("WRR_RESP")

    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()

    engine = RuleEngine(store, mock_enc, mock_srv, None,
                        decoder=mock_dec, ws_hub=mock_ws)

    await store.save_rule({
        "match_pdu_type": "WRR_REQ",
        "action": "auto_reply",
        "reply_template": "WRR_SUCCESS",
    })

    await engine.evaluate(_msg(), None)

    assert mock_ws.broadcast.called
    # One call for the outbound message, one for rule_fired
    assert mock_ws.broadcast.call_count >= 2


async def test_auto_reply_rule_fired_broadcast_payload():
    """The rule_fired broadcast must include rule_id and message_id."""
    store = Store(":memory:")
    await store.init_db()

    mock_enc = MagicMock()
    mock_enc.encode = MagicMock(return_value=b"\xaa\xbb")

    mock_srv = MagicMock()
    mock_srv.send_to_peer = AsyncMock()

    mock_dec = _make_decoder("WRR_RESP")

    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()

    engine = RuleEngine(store, mock_enc, mock_srv, None,
                        decoder=mock_dec, ws_hub=mock_ws)

    rule_row = await store.save_rule({
        "match_pdu_type": "WRR_REQ",
        "action": "auto_reply",
        "reply_template": "WRR_SUCCESS",
    })
    rule_id = rule_row["id"]

    inbound = _msg(id=42)
    await engine.evaluate(inbound, None)

    broadcast_calls = [c.args[0] for c in mock_ws.broadcast.call_args_list]
    rule_fired_events = [c for c in broadcast_calls if c.get("type") == "rule_fired"]
    assert len(rule_fired_events) == 1
    assert rule_fired_events[0]["data"]["rule_id"] == rule_id
    assert rule_fired_events[0]["data"]["message_id"] == 42


# ---------------------------------------------------------------------------
# End-to-end pipeline: WRR_REQ inbound → WRR_SUCCESS outbound → store has both
# ---------------------------------------------------------------------------

async def test_wrr_req_to_wrr_success_full_pipeline():
    """Simulate the full Phase 11 flow:
    inbound WRR_REQ saved → rule fires → WRR_SUCCESS sent and logged outbound.
    """
    store = Store(":memory:")
    await store.init_db()

    mock_enc = MagicMock()
    mock_enc.encode = MagicMock(return_value=b"\x00\x01\x02\x03")

    mock_srv = MagicMock()
    mock_srv.send_to_peer = AsyncMock()

    mock_dec = _make_decoder("WRR_RESP")

    mock_ws = MagicMock()
    mock_ws.broadcast = AsyncMock()

    engine = RuleEngine(store, mock_enc, mock_srv, None,
                        decoder=mock_dec, ws_hub=mock_ws)

    await store.save_rule({
        "match_pdu_type": "WRR_REQ",
        "action": "auto_reply",
        "reply_template": "WRR_SUCCESS",
        "count": 0,
    })

    # Simulate the _on_message callback saving the inbound message
    inbound_dict = {
        "session_id": "s1",
        "timestamp": "2026-03-27T12:00:00+00:00",
        "direction": "inbound",
        "transport": "sctp",
        "local_port": 29168,
        "peer_addr": "127.0.0.1:54321",
        "protocol": "SBc-AP",
        "pdu_type": "WRR_REQ",
        "message_identifier": "0x1144",
        "serial_number": "0x0001",
        "decoded": {},
        "raw_hex": "deadbeef",
        "raw_bytes_b64": "",
    }
    saved_inbound = await store.save_message(inbound_dict)
    await engine.evaluate(saved_inbound, None)

    msgs = await store.get_messages()
    directions = [m["direction"] for m in msgs]
    assert "inbound" in directions
    assert "outbound" in directions

    outbound = next(m for m in msgs if m["direction"] == "outbound")
    assert outbound["pdu_type"] == "WRR_RESP"
    assert outbound["rule_id"] == saved_inbound.get("id") or outbound.get("rule_id") is not None

    # send_to_peer called with correct peer
    mock_srv.send_to_peer.assert_called_once_with("127.0.0.1:54321", b"\x00\x01\x02\x03")


# ---------------------------------------------------------------------------
# No-decoder path: auto_reply without decoder must still send but skip logging
# ---------------------------------------------------------------------------

async def test_auto_reply_without_decoder_still_sends():
    """If decoder is None (legacy construction), send still happens — no crash."""
    store = Store(":memory:")
    await store.init_db()

    mock_enc = MagicMock()
    mock_enc.encode = MagicMock(return_value=b"\xff\xfe")

    mock_srv = MagicMock()
    mock_srv.send_to_peer = AsyncMock()

    engine = RuleEngine(store, mock_enc, mock_srv, None)  # no decoder, no ws_hub

    await store.save_rule({
        "match_pdu_type": "WRR_REQ",
        "action": "auto_reply",
        "reply_template": "WRR_SUCCESS",
    })

    await engine.evaluate(_msg(), None)

    mock_srv.send_to_peer.assert_called_once()
    msgs = await store.get_messages()
    # No outbound message saved (decoder was None)
    assert all(m["direction"] != "outbound" for m in msgs)
