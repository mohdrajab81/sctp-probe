"""Session control — reset generates a new session UUID."""
from __future__ import annotations

from sctp_probe.store import Store


async def reset(store: Store) -> dict:
    new_id, msg_count, rule_count = await store.reset_session()
    return {
        "session_id": new_id,
        "cleared_messages": msg_count,
        "cleared_rules": rule_count,
    }
