"""SQLite persistence layer. All public methods are async via asyncio.to_thread."""
import asyncio
import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

_CREATE_MESSAGES = """
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT    NOT NULL,
    timestamp       TEXT    NOT NULL,
    direction       TEXT    NOT NULL,
    transport       TEXT    NOT NULL DEFAULT 'sctp',
    local_port      INTEGER,
    peer_addr       TEXT,
    protocol        TEXT    NOT NULL DEFAULT 'raw',
    pdu_type        TEXT,
    message_identifier TEXT,
    serial_number   TEXT,
    decoded         TEXT,
    raw_hex         TEXT    NOT NULL DEFAULT '',
    raw_bytes_b64   TEXT    NOT NULL DEFAULT '',
    rule_id         INTEGER
)
"""

_CREATE_RULES = """
CREATE TABLE IF NOT EXISTS rules (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    active                  INTEGER NOT NULL DEFAULT 1,
    match_pdu_type          TEXT    NOT NULL DEFAULT '*',
    match_message_identifier TEXT,
    match_serial_number     TEXT,
    match_peer_addr         TEXT,
    action                  TEXT    NOT NULL DEFAULT 'auto_reply',
    reply_template          TEXT,
    delay_ms                INTEGER NOT NULL DEFAULT 0,
    count                   INTEGER NOT NULL DEFAULT 0,
    fired                   INTEGER NOT NULL DEFAULT 0
)
"""

_CREATE_META = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
"""


class Store:
    def __init__(self, db_path: str = "sctp_probe.db") -> None:
        self._db_path = db_path
        # For :memory: databases, reuse a single connection — separate connections
        # each get their own independent database. A threading.Lock serialises all
        # sync operations so concurrent to_thread calls don't race on the connection.
        self._shared_conn: sqlite3.Connection | None = None
        self._conn_lock = threading.Lock()
        if db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row

    # ------------------------------------------------------------------
    # Internal helpers (called inside asyncio.to_thread)
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _maybe_close(self, conn: sqlite3.Connection) -> None:
        if conn is not self._shared_conn:
            conn.close()

    def _init_db_sync(self) -> None:
        with self._conn_lock:
            conn = self._connect()
            conn.execute(_CREATE_MESSAGES)
            conn.execute(_CREATE_RULES)
            conn.execute(_CREATE_META)
            conn.execute(
                "INSERT OR IGNORE INTO meta (key, value) VALUES ('session_id', ?)",
                (str(uuid.uuid4()),),
            )
            conn.commit()
            self._maybe_close(conn)

    def _get_session_id_sync(self) -> str:
        with self._conn_lock:
            conn = self._connect()
            try:
                row = conn.execute("SELECT value FROM meta WHERE key='session_id'").fetchone()
                return row["value"] if row else str(uuid.uuid4())
            finally:
                self._maybe_close(conn)

    def _save_message_sync(self, msg: dict[str, Any]) -> dict[str, Any]:
        with self._conn_lock:
            conn = self._connect()
            try:
                decoded_json = json.dumps(msg.get("decoded"), default=lambda v: v.hex() if isinstance(v, (bytes, bytearray)) else repr(v)) if msg.get("decoded") is not None else None
                cur = conn.execute(
                    """INSERT INTO messages
                       (session_id, timestamp, direction, transport, local_port, peer_addr,
                        protocol, pdu_type, message_identifier, serial_number,
                        decoded, raw_hex, raw_bytes_b64, rule_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        msg.get("session_id", ""),
                        msg.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        msg.get("direction", "inbound"),
                        msg.get("transport", "sctp"),
                        msg.get("local_port"),
                        msg.get("peer_addr"),
                        msg.get("protocol", "raw"),
                        msg.get("pdu_type"),
                        msg.get("message_identifier"),
                        msg.get("serial_number"),
                        decoded_json,
                        msg.get("raw_hex", ""),
                        msg.get("raw_bytes_b64", ""),
                        msg.get("rule_id"),
                    ),
                )
                conn.commit()
                row = conn.execute("SELECT * FROM messages WHERE id=?", (cur.lastrowid,)).fetchone()
                return self._row_to_msg(row)
            finally:
                self._maybe_close(conn)

    def _get_messages_sync(
        self,
        since_id: int = 0,
        direction: str | None = None,
        pdu_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with self._conn_lock:
            conn = self._connect()
            try:
                clauses = ["id > ?"]
                params: list[Any] = [since_id]
                if direction:
                    clauses.append("direction = ?")
                    params.append(direction)
                if pdu_type:
                    clauses.append("pdu_type = ?")
                    params.append(pdu_type)
                where = " AND ".join(clauses)
                limit = min(max(1, limit), 1000)
                params.append(limit)
                rows = conn.execute(
                    f"SELECT * FROM messages WHERE {where} ORDER BY id ASC LIMIT ?", params
                ).fetchall()
                return [self._row_to_msg(r) for r in rows]
            finally:
                self._maybe_close(conn)

    def _save_rule_sync(self, rule: dict[str, Any]) -> dict[str, Any]:
        with self._conn_lock:
            conn = self._connect()
            try:
                cur = conn.execute(
                    """INSERT INTO rules
                       (active, match_pdu_type, match_message_identifier, match_serial_number,
                        match_peer_addr, action, reply_template, delay_ms, count, fired)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        1 if rule.get("active", True) else 0,
                        rule.get("match_pdu_type", "*"),
                        rule.get("match_message_identifier"),
                        rule.get("match_serial_number"),
                        rule.get("match_peer_addr"),
                        rule.get("action", "auto_reply"),
                        rule.get("reply_template"),
                        rule.get("delay_ms", 0),
                        rule.get("count", 0),
                        0,
                    ),
                )
                conn.commit()
                row = conn.execute("SELECT * FROM rules WHERE id=?", (cur.lastrowid,)).fetchone()
                return self._row_to_rule(row)
            finally:
                self._maybe_close(conn)

    def _get_rules_sync(self) -> list[dict[str, Any]]:
        with self._conn_lock:
            conn = self._connect()
            try:
                rows = conn.execute("SELECT * FROM rules WHERE active=1 ORDER BY id ASC").fetchall()
                return [self._row_to_rule(r) for r in rows]
            finally:
                self._maybe_close(conn)

    def _delete_rule_sync(self, rule_id: int) -> int:
        with self._conn_lock:
            conn = self._connect()
            try:
                cur = conn.execute("DELETE FROM rules WHERE id=?", (rule_id,))
                conn.commit()
                return cur.rowcount
            finally:
                self._maybe_close(conn)

    def _delete_all_rules_sync(self) -> int:
        with self._conn_lock:
            conn = self._connect()
            try:
                cur = conn.execute("DELETE FROM rules")
                conn.commit()
                return cur.rowcount
            finally:
                self._maybe_close(conn)

    def _delete_all_messages_sync(self) -> int:
        with self._conn_lock:
            conn = self._connect()
            try:
                cur = conn.execute("DELETE FROM messages")
                conn.commit()
                return cur.rowcount
            finally:
                self._maybe_close(conn)

    def _reset_session_sync(self) -> tuple[str, int, int]:
        with self._conn_lock:
            conn = self._connect()
            try:
                new_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT OR REPLACE INTO meta (key,value) VALUES ('session_id',?)", (new_id,)
                )
                msg_count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
                rule_count = conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0]
                conn.execute("DELETE FROM rules")
                conn.commit()
                return new_id, msg_count, rule_count
            finally:
                self._maybe_close(conn)

    def _increment_fired_sync(self, rule_id: int) -> None:
        with self._conn_lock:
            conn = self._connect()
            try:
                conn.execute("UPDATE rules SET fired=fired+1 WHERE id=?", (rule_id,))
                conn.commit()
            finally:
                self._maybe_close(conn)

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def init_db(self) -> None:
        await asyncio.to_thread(self._init_db_sync)

    async def get_current_session_id(self) -> str:
        return await asyncio.to_thread(self._get_session_id_sync)

    async def save_message(self, msg: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._save_message_sync, msg)

    async def get_messages(
        self,
        since_id: int = 0,
        direction: str | None = None,
        pdu_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_messages_sync, since_id, direction, pdu_type, limit)

    async def save_rule(self, rule: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._save_rule_sync, rule)

    async def get_rules(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._get_rules_sync)

    async def delete_rule(self, rule_id: int) -> int:
        return await asyncio.to_thread(self._delete_rule_sync, rule_id)

    async def delete_all_rules(self) -> int:
        return await asyncio.to_thread(self._delete_all_rules_sync)

    async def delete_all_messages(self) -> int:
        return await asyncio.to_thread(self._delete_all_messages_sync)

    async def reset_session(self) -> tuple[str, int, int]:
        return await asyncio.to_thread(self._reset_session_sync)

    async def increment_fired(self, rule_id: int) -> None:
        await asyncio.to_thread(self._increment_fired_sync, rule_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_msg(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        if d.get("decoded") and isinstance(d["decoded"], str):
            try:
                d["decoded"] = json.loads(d["decoded"])
            except Exception:
                pass
        return d

    @staticmethod
    def _row_to_rule(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["active"] = bool(d.get("active", 1))
        return d
