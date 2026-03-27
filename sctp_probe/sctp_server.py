"""SCTP server — multi-port listener with asyncio task per connection.

Graceful degradation: if pysctp is not available (non-Linux or module not loaded),
all methods raise SCTPUnavailableError. The FastAPI app still starts normally.
"""
from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any, Callable

log = logging.getLogger(__name__)

try:
    import sctp as _sctp_mod  # type: ignore
    SCTP_AVAILABLE = True
except ImportError:
    SCTP_AVAILABLE = False
    _sctp_mod = None


class SCTPUnavailableError(RuntimeError):
    """Raised when pysctp is not importable or SCTP kernel module is not loaded."""


_SOCKET_TIMEOUT = 5.0


class SctpServer:
    def __init__(self) -> None:
        # port → {"socket": sock, "ppid": int, "task": asyncio.Task, "peers": {addr: conn}}
        self._listeners: dict[int, dict[str, Any]] = {}
        self.on_message: Callable[[bytes, str, int], Any] | None = None
        self.on_event: Callable[[str, str, int], Any] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self, port: int, ppid: int) -> None:
        if not SCTP_AVAILABLE:
            raise SCTPUnavailableError(
                "pysctp is not available. Install libsctp-dev and run 'modprobe sctp'."
            )
        if port in self._listeners:
            raise ValueError(f"Already listening on port {port}")

        sock = await asyncio.to_thread(self._create_listener, port, ppid)
        task = asyncio.get_event_loop().create_task(
            self._accept_loop(port), name=f"sctp-accept-{port}"
        )
        self._listeners[port] = {"socket": sock, "ppid": ppid, "task": task, "peers": {}}
        log.info("SCTP server listening on port %d (ppid=%d)", port, ppid)

    async def stop(self, port: int) -> None:
        entry = self._listeners.pop(port, None)
        if entry is None:
            return
        # Close the listening socket first — this unblocks the accept() thread.
        await asyncio.to_thread(self._close_socket, entry["socket"])
        entry["task"].cancel()
        # Close all accepted peer connections so blocking sctp_recv threads exit.
        peers = list(entry.get("peers", {}).values())
        if peers:
            await asyncio.gather(*(asyncio.to_thread(self._close_socket, c) for c in peers))
        # Wait for the thread pool threads (accept, sctp_recv) to finish exiting
        # after their blocking calls return with an error from the closed socket.
        await asyncio.sleep(0.15)
        log.info("SCTP server stopped on port %d", port)

    async def stop_all(self) -> None:
        for port in list(self._listeners):
            await self.stop(port)

    def status(self) -> list[dict[str, Any]]:
        result = []
        for port, entry in self._listeners.items():
            result.append({
                "port": port,
                "ppid": entry["ppid"],
                "peers": list(entry["peers"].keys()),
            })
        return result

    async def send_to_peer(self, peer_addr: str, raw_bytes: bytes) -> None:
        """Send raw bytes to a connected peer. peer_addr is 'ip:port'."""
        for entry in self._listeners.values():
            conn = entry["peers"].get(peer_addr)
            if conn is not None:
                await asyncio.to_thread(conn.send, raw_bytes)
                return
        log.warning("send_to_peer: peer %s not found", peer_addr)

    # ------------------------------------------------------------------
    # Internal (run in thread or as tasks)
    # ------------------------------------------------------------------

    def _create_listener(self, port: int, ppid: int) -> Any:
        sock = _sctp_mod.sctpsocket_tcp(socket.AF_INET)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(_SOCKET_TIMEOUT)
        sock.bind(("127.0.0.1", port))
        sock.listen(16)
        return sock

    @staticmethod
    def _close_socket(sock: Any) -> None:
        try:
            sock.close()
        except Exception:
            pass

    async def _accept_loop(self, port: int) -> None:
        entry = self._listeners.get(port)
        if entry is None:
            return
        sock = entry["socket"]
        while True:
            try:
                conn, peer = await asyncio.to_thread(sock.accept)
                # Listening socket has a timeout (non-blocking mode for accept);
                # accepted connections must be blocking for sctp_recv to work.
                conn.setblocking(True)
                peer_addr = f"{peer[0]}:{peer[1]}"
                entry["peers"][peer_addr] = conn
                log.info("SCTP assoc up: %s on port %d", peer_addr, port)
                if self.on_event:
                    asyncio.get_event_loop().create_task(
                        self._call_cb(self.on_event, "assoc_up", peer_addr, port)
                    )
                asyncio.get_event_loop().create_task(
                    self._handle_conn(conn, peer_addr, port),
                    name=f"sctp-conn-{peer_addr}",
                )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.debug("accept_loop port %d: %s", port, exc)
                await asyncio.sleep(0.1)

    async def _handle_conn(self, conn: Any, peer_addr: str, port: int) -> None:
        # Use the underlying SOCK_STREAM socket recv() directly.
        # pysctp's sctp_recv() returns (flags=0x0, msg=b"") for ancillary-data
        # frames sent by ishidawataru/sctp (SCTPWrite with PPID cmsg), causing a
        # busy-spin. The raw recv() reads the actual payload bytes reliably because
        # TCP-style SCTP is byte-stream compatible with plain socket.recv().
        raw_sock = conn._sk  # pysctp sctpsocket wraps a standard socket in _sk
        log.debug("_handle_conn started for %s port %d", peer_addr, port)
        try:
            while True:
                try:
                    raw = await asyncio.to_thread(raw_sock.recv, 65535)
                except socket.timeout:
                    continue
                except Exception as exc:
                    log.debug("recv from %s: %s", peer_addr, exc)
                    break
                if not raw:
                    break  # clean EOF — peer closed
                log.debug("recv %d bytes from %s port %d hex=%s", len(raw), peer_addr, port, raw.hex()[:40])
                if self.on_message:
                    await self._call_cb(self.on_message, raw, peer_addr, port)
        finally:
            entry = self._listeners.get(port, {})
            entry.get("peers", {}).pop(peer_addr, None)
            await asyncio.to_thread(self._close_socket, conn)
            log.info("SCTP assoc down: %s on port %d", peer_addr, port)
            if self.on_event:
                asyncio.get_event_loop().create_task(
                    self._call_cb(self.on_event, "assoc_down", peer_addr, port)
                )

    @staticmethod
    async def _call_cb(cb: Callable, *args: Any) -> None:
        try:
            result = cb(*args)
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:
            log.error("SCTP callback error: %s", exc)
