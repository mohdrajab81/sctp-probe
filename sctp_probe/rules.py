"""Rule engine — evaluate inbound messages against configured rules."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)


class RuleEngine:
    def __init__(self, store: Any, encoder: Any, sctp_server: Any, sctp_client: Any,
                 decoder: Any = None, ws_hub: Any = None) -> None:
        self._store = store
        self._encoder = encoder
        self._sctp_server = sctp_server
        self._sctp_client = sctp_client
        self._decoder = decoder
        self._ws_hub = ws_hub

    async def evaluate(self, inbound_msg: dict[str, Any], source_conn: Any) -> None:
        """Find the first matching active rule and execute its action."""
        rules = await self._store.get_rules()
        for rule in rules:
            if self._match(rule, inbound_msg):
                await self._execute(rule, inbound_msg, source_conn)
                return  # first-match wins

    def _match(self, rule: dict[str, Any], msg: dict[str, Any]) -> bool:
        """Pure matching function — no I/O."""
        if not rule.get("active", True):
            return False

        pdu_filter = rule.get("match_pdu_type", "*")
        if pdu_filter != "*" and pdu_filter != msg.get("pdu_type"):
            return False

        mi_filter = rule.get("match_message_identifier")
        if mi_filter is not None and mi_filter != msg.get("message_identifier"):
            return False

        sn_filter = rule.get("match_serial_number")
        if sn_filter is not None and sn_filter != msg.get("serial_number"):
            return False

        peer_filter = rule.get("match_peer_addr")
        if peer_filter is not None and peer_filter != msg.get("peer_addr"):
            return False

        count = rule.get("count", 0)
        fired = rule.get("fired", 0)
        if count != 0 and fired >= count:
            return False

        return True

    async def _execute(
        self,
        rule: dict[str, Any],
        msg: dict[str, Any],
        source_conn: Any,
    ) -> None:
        rule_id = rule["id"]
        action = rule.get("action", "log_only")
        delay_ms = rule.get("delay_ms", 0)

        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)

        await self._store.increment_fired(rule_id)

        if action == "drop":
            log.debug("rule %d: drop, message_id=%s", rule_id, msg.get("id"))
            return

        if action == "log_only":
            log.debug("rule %d: log_only, message_id=%s", rule_id, msg.get("id"))
            return

        if action == "auto_reply":
            template = rule.get("reply_template")
            if not template:
                log.warning("rule %d: auto_reply but no reply_template set", rule_id)
                return

            from sctp_probe.decoder import DecodedMessage
            # Reconstruct a minimal DecodedMessage for MI/SN echo
            dm = DecodedMessage(
                pdu_type=msg.get("pdu_type"),
                message_identifier=msg.get("message_identifier"),
                serial_number=msg.get("serial_number"),
            )
            raw = self._encoder.encode(template, dm)
            if raw is None:
                log.debug("rule %d: template %s produced no bytes (e.g. WRR_TIMEOUT)", rule_id, template)
                return

            try:
                peer_addr = msg.get("peer_addr")
                if peer_addr and hasattr(self._sctp_server, "send_to_peer"):
                    await self._sctp_server.send_to_peer(peer_addr, raw)
                elif source_conn is not None and hasattr(self._sctp_client, "send"):
                    conn_id = getattr(source_conn, "conn_id", None)
                    if conn_id:
                        await self._sctp_client.send(conn_id, raw)
            except Exception as exc:
                log.error("rule %d: send failed: %s", rule_id, exc)
                return

            # Log the outbound reply
            if self._decoder is not None:
                out_dm = self._decoder.decode(raw)
                session_id = await self._store.get_current_session_id()
                out_msg = {
                    "session_id": session_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "direction": "outbound",
                    "transport": msg.get("transport", "sctp"),
                    "local_port": msg.get("local_port"),
                    "peer_addr": msg.get("peer_addr"),
                    "protocol": out_dm.protocol,
                    "pdu_type": out_dm.pdu_type,
                    "message_identifier": out_dm.message_identifier,
                    "serial_number": out_dm.serial_number,
                    "decoded": out_dm.decoded,
                    "raw_hex": out_dm.raw_hex,
                    "raw_bytes_b64": out_dm.raw_bytes_b64,
                    "rule_id": rule_id,
                }
                saved = await self._store.save_message(out_msg)
                if self._ws_hub is not None:
                    await self._ws_hub.broadcast({"type": "message", "data": saved})
                    await self._ws_hub.broadcast({"type": "rule_fired",
                                                   "data": {"rule_id": rule_id,
                                                            "message_id": msg.get("id")}})
