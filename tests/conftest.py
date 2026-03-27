"""pytest fixtures shared across all test modules."""
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock

from sctp_probe.store import Store


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "sctp: marks tests as requiring Linux SCTP kernel support"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as requiring live sctp-probe + SentinelCBC + Postgres"
    )


@pytest.fixture
async def store():
    s = Store(":memory:")
    await s.init_db()
    return s


@pytest.fixture
def mock_sctp_server():
    srv = MagicMock()
    srv.start = AsyncMock()
    srv.stop = AsyncMock()
    srv.stop_all = AsyncMock()
    srv.send_to_peer = AsyncMock()
    srv.status = MagicMock(return_value=[])
    srv._listeners = {}
    return srv


@pytest.fixture
def mock_sctp_client():
    cli = MagicMock()
    cli.connect = AsyncMock(return_value="conn-1")
    cli.disconnect = AsyncMock()
    cli.disconnect_all = AsyncMock()
    cli.send = AsyncMock()
    cli.status = MagicMock(return_value=[])
    cli._conns = {}
    return cli
