from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError

from app.api.routes import health
from app.core.config import get_settings
from app.main import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "test-only")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    get_settings.cache_clear()


async def test_liveness_does_not_access_database(client, monkeypatch):
    engine = MagicMock(side_effect=AssertionError("Must not access database"))
    monkeypatch.setattr(health, "get_engine", engine)
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    engine.assert_not_called()


async def test_readiness_returns_503_without_leaking_database_error(client, monkeypatch):
    engine = MagicMock()
    engine.connect.side_effect = OperationalError("SELECT 1", {}, Exception("secret-host"))
    monkeypatch.setattr(health, "get_engine", lambda: engine)
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Service unavailable"}
    assert "secret-host" not in response.text


async def test_readiness_queries_database(client, monkeypatch):
    engine = MagicMock()
    monkeypatch.setattr(health, "get_engine", lambda: engine)
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    engine.connect.return_value.__enter__.return_value.execute.assert_called_once()
