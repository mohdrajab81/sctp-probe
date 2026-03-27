"""Tests for store.py — all use in-memory SQLite, run on any OS."""
import asyncio
import pytest
from sctp_probe.store import Store


@pytest.fixture
async def s():
    store = Store(":memory:")
    await store.init_db()
    return store


def _msg(**kwargs):
    base = {
        "session_id": "test-session",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "direction": "inbound",
        "transport": "sctp",
        "local_port": 29168,
        "peer_addr": "127.0.0.1:54321",
        "protocol": "SBc-AP",
        "pdu_type": "WRR_REQ",
        "message_identifier": "0x1144",
        "serial_number": "0x0001",
        "decoded": {"Cause": 0},
        "raw_hex": "00 01",
        "raw_bytes_b64": "AAE=",
    }
    base.update(kwargs)
    return base


async def test_save_and_get_messages(s):
    saved = await s.save_message(_msg())
    assert saved["id"] == 1
    msgs = await s.get_messages()
    assert len(msgs) == 1
    assert msgs[0]["pdu_type"] == "WRR_REQ"
    assert msgs[0]["decoded"] == {"Cause": 0}


async def test_since_id_filter(s):
    await s.save_message(_msg())
    await s.save_message(_msg())
    await s.save_message(_msg())
    msgs = await s.get_messages(since_id=1)
    assert len(msgs) == 2
    assert all(m["id"] > 1 for m in msgs)


async def test_direction_filter(s):
    await s.save_message(_msg(direction="inbound"))
    await s.save_message(_msg(direction="outbound"))
    inbound = await s.get_messages(direction="inbound")
    assert all(m["direction"] == "inbound" for m in inbound)
    assert len(inbound) == 1


async def test_pdu_type_filter(s):
    await s.save_message(_msg(pdu_type="WRR_REQ"))
    await s.save_message(_msg(pdu_type="SWR_REQ"))
    wrr = await s.get_messages(pdu_type="WRR_REQ")
    assert len(wrr) == 1
    assert wrr[0]["pdu_type"] == "WRR_REQ"


async def test_save_and_delete_rule(s):
    rule = await s.save_rule({
        "match_pdu_type": "WRR_REQ",
        "action": "auto_reply",
        "reply_template": "WRR_SUCCESS",
    })
    assert rule["id"] == 1
    rules = await s.get_rules()
    assert len(rules) == 1
    deleted = await s.delete_rule(rule["id"])
    assert deleted == 1
    assert await s.get_rules() == []


async def test_delete_all_rules(s):
    await s.save_rule({"match_pdu_type": "*", "action": "log_only"})
    await s.save_rule({"match_pdu_type": "SWR_REQ", "action": "drop"})
    deleted = await s.delete_all_rules()
    assert deleted == 2
    assert await s.get_rules() == []


async def test_reset_session_clears_rules_not_messages(s):
    await s.save_message(_msg())
    await s.save_message(_msg())
    await s.save_rule({"match_pdu_type": "*", "action": "log_only"})

    new_id, msg_count, rule_count = await s.reset_session()

    assert len(new_id) > 0
    assert msg_count == 2
    assert rule_count == 1
    # Messages still exist
    msgs = await s.get_messages()
    assert len(msgs) == 2
    # Rules are cleared
    assert await s.get_rules() == []


async def test_increment_fired(s):
    rule = await s.save_rule({"match_pdu_type": "*", "action": "log_only"})
    await s.increment_fired(rule["id"])
    await s.increment_fired(rule["id"])
    rules = await s.get_rules()
    assert rules[0]["fired"] == 2


async def test_delete_all_messages(s):
    await s.save_message(_msg())
    await s.save_message(_msg())
    deleted = await s.delete_all_messages()
    assert deleted == 2
    assert await s.get_messages() == []


async def test_concurrent_inserts(s):
    tasks = [s.save_message(_msg(pdu_type=f"T{i}")) for i in range(20)]
    results = await asyncio.gather(*tasks)
    ids = [r["id"] for r in results]
    assert len(set(ids)) == 20  # all unique IDs
    msgs = await s.get_messages(limit=30)
    assert len(msgs) == 20


async def test_session_id_is_stable(s):
    id1 = await s.get_current_session_id()
    id2 = await s.get_current_session_id()
    assert id1 == id2
    assert len(id1) == 36  # UUID format
