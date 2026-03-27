"""Tests for rules.py — run on any OS."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sctp_probe.rules import RuleEngine
from sctp_probe.store import Store


@pytest.fixture
async def engine_with_store():
    store = Store(":memory:")
    await store.init_db()
    mock_enc = MagicMock()
    mock_enc.encode = MagicMock(return_value=b"\x00\x01\x02")
    mock_srv = MagicMock()
    mock_srv.send_to_peer = AsyncMock()
    mock_cli = MagicMock()
    engine = RuleEngine(store, mock_enc, mock_srv, mock_cli)
    return engine, store, mock_srv


def _msg(**kwargs):
    base = {
        "id": 1,
        "session_id": "s1",
        "direction": "inbound",
        "pdu_type": "WRR_REQ",
        "message_identifier": "0x1144",
        "serial_number": "0x0001",
        "peer_addr": "127.0.0.1:54321",
    }
    base.update(kwargs)
    return base


def _rule(**kwargs):
    base = {
        "id": 1,
        "active": True,
        "match_pdu_type": "*",
        "match_message_identifier": None,
        "match_serial_number": None,
        "match_peer_addr": None,
        "action": "log_only",
        "reply_template": None,
        "delay_ms": 0,
        "count": 0,
        "fired": 0,
    }
    base.update(kwargs)
    return base


# ------------------------------------------------------------------
# _match unit tests
# ------------------------------------------------------------------

def test_match_wildcard():
    engine = RuleEngine(None, None, None, None)
    rule = _rule(match_pdu_type="*")
    assert engine._match(rule, _msg(pdu_type="WRR_REQ"))
    assert engine._match(rule, _msg(pdu_type="SWR_REQ"))


def test_match_specific_pdu_type():
    engine = RuleEngine(None, None, None, None)
    rule = _rule(match_pdu_type="WRR_REQ")
    assert engine._match(rule, _msg(pdu_type="WRR_REQ"))
    assert not engine._match(rule, _msg(pdu_type="SWR_REQ"))


def test_match_message_identifier():
    engine = RuleEngine(None, None, None, None)
    rule = _rule(match_message_identifier="0x1144")
    assert engine._match(rule, _msg(message_identifier="0x1144"))
    assert not engine._match(rule, _msg(message_identifier="0x9999"))


def test_match_serial_number():
    engine = RuleEngine(None, None, None, None)
    rule = _rule(match_serial_number="0x0001")
    assert engine._match(rule, _msg(serial_number="0x0001"))
    assert not engine._match(rule, _msg(serial_number="0x0002"))


def test_match_peer_addr():
    engine = RuleEngine(None, None, None, None)
    rule = _rule(match_peer_addr="127.0.0.1:54321")
    assert engine._match(rule, _msg(peer_addr="127.0.0.1:54321"))
    assert not engine._match(rule, _msg(peer_addr="10.0.0.1:12345"))


def test_no_match_inactive_rule():
    engine = RuleEngine(None, None, None, None)
    rule = _rule(active=False)
    assert not engine._match(rule, _msg())


def test_count_limit():
    engine = RuleEngine(None, None, None, None)
    rule = _rule(count=2, fired=2)
    assert not engine._match(rule, _msg())
    rule2 = _rule(count=2, fired=1)
    assert engine._match(rule2, _msg())


# ------------------------------------------------------------------
# evaluate integration tests
# ------------------------------------------------------------------

async def test_drop_action_no_reply(engine_with_store):
    engine, store, mock_srv = engine_with_store
    await store.save_rule({
        "match_pdu_type": "WRR_REQ",
        "action": "drop",
        "reply_template": None,
    })
    await engine.evaluate(_msg(), None)
    mock_srv.send_to_peer.assert_not_called()


async def test_auto_reply_sends_bytes(engine_with_store):
    engine, store, mock_srv = engine_with_store
    await store.save_rule({
        "match_pdu_type": "WRR_REQ",
        "action": "auto_reply",
        "reply_template": "WRR_SUCCESS",
    })
    msg = _msg(peer_addr="127.0.0.1:54321")
    await engine.evaluate(msg, None)
    mock_srv.send_to_peer.assert_called_once()
    call_args = mock_srv.send_to_peer.call_args[0]
    assert call_args[0] == "127.0.0.1:54321"
    assert isinstance(call_args[1], bytes)


async def test_first_match_wins(engine_with_store):
    engine, store, mock_srv = engine_with_store
    await store.save_rule({"match_pdu_type": "WRR_REQ", "action": "drop"})
    await store.save_rule({"match_pdu_type": "WRR_REQ", "action": "auto_reply", "reply_template": "WRR_SUCCESS"})
    await engine.evaluate(_msg(), None)
    # Drop rule fires first — no reply
    mock_srv.send_to_peer.assert_not_called()


async def test_count_limiting_via_evaluate(engine_with_store):
    engine, store, mock_srv = engine_with_store
    await store.save_rule({
        "match_pdu_type": "WRR_REQ",
        "action": "auto_reply",
        "reply_template": "WRR_SUCCESS",
        "count": 1,
    })
    await engine.evaluate(_msg(), None)
    await engine.evaluate(_msg(), None)
    # Only one send — second call should not match (count exhausted)
    assert mock_srv.send_to_peer.call_count == 1


async def test_no_rule_no_reply(engine_with_store):
    engine, store, mock_srv = engine_with_store
    await engine.evaluate(_msg(), None)
    mock_srv.send_to_peer.assert_not_called()
