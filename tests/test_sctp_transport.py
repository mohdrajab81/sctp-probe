"""SCTP transport smoke tests — require Linux SCTP kernel support.

Run with:
    pytest tests/test_sctp_transport.py -v -m sctp

These tests are skipped automatically when pysctp is unavailable.
"""
import asyncio
import socket
import pytest

pytestmark = pytest.mark.sctp


@pytest.fixture(autouse=True)
def require_sctp():
    try:
        import sctp  # noqa: F401
    except ImportError:
        pytest.skip("pysctp not available — skipping SCTP transport tests")


def _free_port() -> int:
    """Return a port number that is free at the time of the call.

    We bind a TCP socket to port 0, read the assigned port, then close it.
    Immediately using it for SCTP is not perfectly race-free, but in practice
    the OS does not immediately reassign the port.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def test_server_client_roundtrip():
    """Start server, connect client, send in both directions, disconnect cleanly."""
    from sctp_probe.sctp_server import SctpServer
    from sctp_probe.sctp_client import SctpClient

    received_by_server: list[bytes] = []
    received_by_client: list[bytes] = []

    server = SctpServer()
    client = SctpClient()

    # on_message(raw, peer_addr, local_port)
    def on_server_message(raw: bytes, peer_addr: str, local_port: int) -> None:
        received_by_server.append(raw)

    # on_message(raw, peer_addr, port)
    def on_client_message(raw: bytes, peer_addr: str, port: int) -> None:
        received_by_client.append(raw)

    server.on_message = on_server_message
    client.on_message = on_client_message

    port = _free_port()
    conn_id = None

    try:
        await server.start(port, ppid=24)
        conn_id = await client.connect("127.0.0.1", port, ppid=24)

        # Allow the accept loop to pick up the connection
        await asyncio.sleep(0.3)

        # Client → server
        await client.send(conn_id, b"hello sctp")
        await asyncio.sleep(0.3)
        assert b"hello sctp" in received_by_server, (
            f"Server did not receive message; got: {received_by_server}"
        )

        # Server → client: find the peer addr for this client connection
        entry = server._listeners.get(port, {})
        peers = entry.get("peers", {})
        assert peers, "Server has no connected peers"
        peer_addr = next(iter(peers))
        await server.send_to_peer(peer_addr, b"hello back")
        await asyncio.sleep(0.3)
        assert b"hello back" in received_by_client, (
            f"Client did not receive reply; got: {received_by_client}"
        )

    finally:
        if conn_id is not None:
            await client.disconnect(conn_id)
        await server.stop(port)


async def test_client_disconnect_no_error():
    """Disconnect a connected client without errors."""
    from sctp_probe.sctp_server import SctpServer
    from sctp_probe.sctp_client import SctpClient

    server = SctpServer()
    client = SctpClient()
    port = _free_port()

    try:
        await server.start(port, ppid=24)
        conn_id = await client.connect("127.0.0.1", port, ppid=24)
        await asyncio.sleep(0.2)
        await client.disconnect(conn_id)
        assert conn_id not in client._conns
    finally:
        await server.stop(port)


async def test_sctp_unavailable_raises():
    """SCTPUnavailableError is raised correctly when SCTP is absent.

    This test only verifies the error path on a non-SCTP platform; on Linux
    with SCTP loaded it just passes trivially.
    """
    from sctp_probe.sctp_server import SCTP_AVAILABLE, SCTPUnavailableError, SctpServer

    if SCTP_AVAILABLE:
        pytest.skip("SCTP is available — unavailable path not reachable")

    server = SctpServer()
    with pytest.raises(SCTPUnavailableError):
        await server.start(_free_port(), ppid=24)