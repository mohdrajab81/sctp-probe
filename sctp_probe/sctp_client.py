"""SCTP client — outgoing associations with heartbeat and read loop.

Must NOT import from sctp_server.py.
"""
from __future__ import annotations

import asyncio
import errno
import itertools
import logging
import socket
from typing import Any, Callable

log = logging.getLogger(__name__)

try:
    import sctp as _sctp_mod  # type: ignore
    _FLAG_NOTIFICATION: int = _sctp_mod.FLAG_NOTIFICATION
    SCTP_AVAILABLE = True
except ImportError:
    SCTP_AVAILABLE = False
    _sctp_mod = None
    _FLAG_NOTIFICATION = 0x8000  # MSG_NOTIFICATION — fallback when pysctp absent

_SOCKET_TIMEOUT = 5.0
_HEARTBEAT_INTERVAL = 10.0
_CONN_ID_COUNTER = itertools.count(1)


class SCTPUnavailableError(RuntimeError):
    """Raised when pysctp is not importable."""


class SctpClient:
    def __init__(self) -> None:
        # conn_id → {socket, host, port, ppid, state, read_task, hb_task}
        self._conns: dict[str, dict[str, Any]] = {}
        self.on_message: Callable[[bytes, str, int], Any] | None = None
        self.on_event: Callable[[str, str, int], Any] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def connect(self, host: str, port: int, ppid: int) -> str:
        if not SCTP_AVAILABLE:
            raise SCTPUnavailableError(
                "pysctp is not available. Install libsctp-dev and run 'modprobe sctp'."
            )
        conn_id = f"conn-{next(_CONN_ID_COUNTER)}"
        sock = await asyncio.to_thread(self._create_conn, host, port, ppid)
        read_task = asyncio.get_event_loop().create_task(
            self._read_loop(conn_id), name=f"sctp-read-{conn_id}"
        )
        hb_task = asyncio.get_event_loop().create_task(
            self._heartbeat_loop(conn_id), name=f"sctp-hb-{conn_id}"
        )
        self._conns[conn_id] = {
            "socket": sock,
            "host": host,
            "port": port,
            "ppid": ppid,
            "state": "CONNECTED",
            "read_task": read_task,
            "hb_task": hb_task,
        }
        log.info("SCTP client connected to %s:%d (id=%s)", host, port, conn_id)
        return conn_id

    async def disconnect(self, conn_id: str) -> None:
        entry = self._conns.pop(conn_id, None)
        if entry is None:
            return
        entry["read_task"].cancel()
        entry["hb_task"].cancel()
        await asyncio.to_thread(self._close_socket, entry["socket"])
        try:
            await asyncio.wait_for(
                asyncio.gather(entry["read_task"], entry["hb_task"], return_exceptions=True),
                timeout=_SOCKET_TIMEOUT + 1.0,
            )
        except asyncio.TimeoutError:
            log.warning("Timed out waiting for SCTP client tasks to stop for %s", conn_id)
        log.info("SCTP client disconnected %s", conn_id)

    async def disconnect_all(self) -> None:
        for conn_id in list(self._conns):
            await self.disconnect(conn_id)

    async def send(self, conn_id: str, raw_bytes: bytes) -> None:
        entry = self._conns.get(conn_id)
        if entry is None:
            raise KeyError(f"Unknown connection id: {conn_id}")
        if entry["state"] != "CONNECTED":
            raise RuntimeError(f"Connection {conn_id} is not in CONNECTED state")
        await asyncio.to_thread(entry["socket"].send, raw_bytes)

    def status(self) -> list[dict[str, Any]]:
        return [
            {
                "id": cid,
                "host": e["host"],
                "port": e["port"],
                "state": e["state"],
            }
            for cid, e in self._conns.items()
        ]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _create_conn(self, host: str, port: int, ppid: int) -> Any:
        sock = _sctp_mod.sctpsocket_tcp(socket.AF_INET)
        sock.settimeout(_SOCKET_TIMEOUT)  # timeout applies to connect()
        sock.connect((host, port))
        sock.settimeout(_SOCKET_TIMEOUT)
        return sock

    @staticmethod
    def _close_socket(sock: Any) -> None:
        sockets = [sock]
        raw_sock = getattr(sock, "_sk", None)
        if raw_sock is not None and raw_sock is not sock:
            sockets.append(raw_sock)
        for candidate in sockets:
            try:
                candidate.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                candidate.close()
            except Exception:
                pass

    async def _read_loop(self, conn_id: str) -> None:
        while True:
            entry = self._conns.get(conn_id)
            if entry is None:
                break
            try:
                result = await asyncio.to_thread(entry["socket"].sctp_recv, 65535)
            except asyncio.CancelledError:
                break
            except socket.timeout:
                continue
            except BlockingIOError:
                continue
            except OSError as exc:
                if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                    continue
                log.debug("sctp_recv client %s: %s", conn_id, exc)
                if conn_id in self._conns:
                    self._conns[conn_id]["state"] = "ERROR"
                break
            except Exception as exc:
                log.debug("sctp_recv client %s: %s", conn_id, exc)
                if conn_id in self._conns:
                    self._conns[conn_id]["state"] = "ERROR"
                break
            # pysctp sctp_recv returns (fromaddr, flags, msg, notif)
            _fromaddr, flags, raw, _notif = result
            if flags & _FLAG_NOTIFICATION:
                continue
            if not raw:
                # Skip zero-length non-notification messages (sndrcvinfo events
                # from the SCTP stack). True close arrives as an exception.
                continue
            if self.on_message:
                entry2 = self._conns.get(conn_id, {})
                peer_addr = f"{entry2.get('host','?')}:{entry2.get('port',0)}"
                await self._call_cb(self.on_message, raw, peer_addr, entry2.get("port", 0))

    async def _heartbeat_loop(self, conn_id: str) -> None:
        while True:
            try:
                await asyncio.sleep(_HEARTBEAT_INTERVAL)
            except asyncio.CancelledError:
                break
            entry = self._conns.get(conn_id)
            if entry is None:
                break
            try:
                # A zero-length send is a liveness probe
                await asyncio.to_thread(entry["socket"].send, b"")
            except Exception:
                if conn_id in self._conns:
                    self._conns[conn_id]["state"] = "ERROR"
                    log.warning("Heartbeat failed for %s — marking ERROR", conn_id)

    @staticmethod
    async def _call_cb(cb: Callable, *args: Any) -> None:
        try:
            result = cb(*args)
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:
            log.error("SCTP client callback error: %s", exc)
