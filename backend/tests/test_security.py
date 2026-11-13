from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.api.dependencies import database_session
from app.core.config import Settings, get_settings
from app.core.security import TokenBuckets
from app.main import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "test-only")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("RATE_LIMIT_BURST", "20")
    monkeypatch.setenv("ALLOWED_HOSTS", '["test","localhost"]')
    get_settings.cache_clear()
    app = create_app()
    yield app
    get_settings.cache_clear()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def test_rate_limit_has_headers_and_ignores_forwarded_identity(client):
    for _ in range(20):
        assert (await client.get("/api/v1/health/live")).status_code == 200
    response = await client.get(
        "/api/v1/health/live",
        headers={"X-Forwarded-For": "192.0.2.40"},
    )
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) >= 1
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert len(response.headers["X-Request-ID"]) == 32


@pytest.mark.parametrize("method", ["DELETE", "PUT", "POST"])
async def test_cors_only_allows_frontend_and_read_methods(client, method):
    headers = {"Origin": "http://localhost:3000"}
    allowed = await client.get("/api/v1/health/live", headers=headers)
    assert allowed.headers["Access-Control-Allow-Origin"] == headers["Origin"]
    blocked = await client.get("/api/v1/health/live", headers={"Origin": "https://evil.test"})
    assert "Access-Control-Allow-Origin" not in blocked.headers
    preflight = await client.options(
        "/api/v1/health/live",
        headers={**headers, "Access-Control-Request-Method": method},
    )
    assert preflight.status_code == 400
    assert (await client.post("/api/v1/health/live")).status_code == 405
    admin = await client.options(
        "/api/v1/analytics/summary",
        headers={
            **headers,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert admin.status_code == 200


async def test_analytics_body_is_bounded_before_parsing(app, monkeypatch):
    from app.api.routes import analytics

    monkeypatch.setattr(analytics, "record", lambda *args: None)
    monkeypatch.setenv("ANALYTICS_ENABLED", "true")
    get_settings.cache_clear()
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        preflight = await client.options(
            "/api/v1/analytics/pageviews",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert preflight.status_code == 200
        response = await client.post(
            "/api/v1/analytics/pageviews",
            content=b"x" * 4097,
            headers={"Content-Type": "application/json", "Origin": "http://localhost:3000"},
        )
        assert response.status_code == 413
        malformed = await client.post(
            "/api/v1/analytics/pageviews",
            content=b"{",
            headers={"Content-Type": "application/json", "Origin": "http://localhost:3000"},
        )
        assert malformed.status_code == 422
        valid = await client.post(
            "/api/v1/analytics/pageviews",
            json={"route": "/"},
            headers={"Origin": "http://localhost:3000"},
        )
        assert valid.status_code == 204

        async def chunks():
            yield b"x" * 3000
            yield b"x" * 1100

        streamed = await client.post(
            "/api/v1/analytics/pageviews",
            content=chunks(),
            headers={"Content-Type": "application/json", "Origin": "http://localhost:3000"},
        )
        assert streamed.status_code == 413


async def test_content_admin_mutations_are_blocked(client):
    oversized = await client.post(
        "/api/v1/content-admin/citizen-explanations/00000000-0000-0000-0000-000000000000/generate-draft",
        content=b"x" * 131073,
        headers={"Content-Type": "application/json"},
    )
    assert oversized.status_code == 405


async def test_host_and_uri_limits(client):
    assert (
        await client.get("/api/v1/health/live", headers={"Host": "evil.test"})
    ).status_code == 400
    assert (await client.get("/api/v1/health/live?q=" + "x" * 8200)).status_code == 414


async def test_cors_on_throttled_response(client):
    for _ in range(20):
        await client.get("/api/v1/health/live")
    response = await client.get(
        "/api/v1/health/live",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 429
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "Retry-After" in response.headers["Access-Control-Expose-Headers"]


async def test_exception_and_request_logs_do_not_disclose_input(app, client, caplog):
    @app.get("/api/v1/failure")
    def failure():
        raise RuntimeError("secret-database-password")

    with caplog.at_level("INFO", logger="app.requests"):
        response = await client.get(
            "/api/v1/failure?token=secret-query",
            headers={"Authorization": "secret-token"},
        )
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "secret-" not in response.text + caplog.text
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Request-ID"] in caplog.text


async def test_interrupted_response_hides_exception_from_server(app, client, caplog):
    import traceback

    from starlette.responses import StreamingResponse

    @app.get("/api/v1/interrupted")
    async def interrupted():
        async def chunks():
            yield b"partial"
            raise ValueError("sensitive-stream-error")

        return StreamingResponse(chunks())

    with pytest.raises(RuntimeError, match="Response interrupted") as error:
        await client.get("/api/v1/interrupted")
    assert "sensitive-stream-error" not in "".join(traceback.format_exception(error.value))
    assert "sensitive-stream-error" not in caplog.text


@pytest.mark.parametrize("suffix", ["pdf", "csv"])
async def test_exports_have_stricter_limit_without_calling_database(app, client, suffix):
    @app.get(f"/api/v1/export.{suffix}")
    def export():
        return {"ok": True}

    assert (await client.get(f"/api/v1/export.{suffix}")).status_code == 200
    assert (await client.get(f"/api/v1/export.{suffix}")).status_code == 200
    response = await client.get(f"/api/v1/export.{suffix}")
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) >= 1


async def test_invalid_pagination_never_executes_query(app, client):
    db = MagicMock()
    app.dependency_overrides[database_session] = lambda: db
    for query in ["limit=101", "offset=-1", "offset=100001", "source=arbitrary", "state=123"]:
        response = await client.get("/api/v1/parliamentarians?" + query)
        assert response.status_code == 422
    assert not db.mock_calls


def test_bucket_refill_capacity_and_client_isolation():
    buckets = TokenBuckets(per_minute=60, burst=2, max_clients=2)
    assert buckets.consume("a", 0) == 0
    assert buckets.consume("a", 0) == 0
    assert buckets.consume("a", 0) == 1
    assert buckets.consume("b", 0) == 0
    assert buckets.consume("c", 0) > 0
    assert len(buckets.clients) == 2
    assert buckets.consume("a", 1) == 0
    assert buckets.consume("c", 3) == 0
    assert len(buckets.clients) <= 2


def test_production_configuration_requires_explicit_security_settings():
    params = {"_env_file": None, "app_env": "production", "db_password": "x" * 32}
    with pytest.raises(ValidationError):
        Settings(**params)
    with pytest.raises(ValidationError):
        Settings(**params, frontend_url="https://portal.example", allowed_hosts=["*"])
    valid = Settings(
        **params, frontend_url="https://portal.example/", allowed_hosts=["api.example"]
    )
    assert valid.frontend_url == "https://portal.example"

    with pytest.raises(ValidationError):
        Settings(
            **params,
            frontend_url="https://portal.example",
            allowed_hosts=["api.example"],
            citizen_explanation_provider="openai",
        )
    configured = Settings(
        **params,
        frontend_url="https://portal.example",
        allowed_hosts=["api.example"],
        citizen_explanation_provider="openai",
        openai_api_key="test-key",
        openai_citizen_generation_model="generation-model",
        openai_citizen_verification_model="verification-model",
    )
    assert configured.citizen_explanation_provider == "openai"


async def test_production_disables_docs_and_sends_hsts(monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "x" * 32)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FRONTEND_URL", "https://portal.example")
    monkeypatch.setenv("ALLOWED_HOSTS", '["api.example"]')
    get_settings.cache_clear()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=create_app()),
            base_url="https://api.example",
        ) as client:
            response = await client.get("/api/v1/health/live")
            assert response.status_code == 200
            assert response.headers["Strict-Transport-Security"] == "max-age=31536000"
            assert (await client.get("/docs")).status_code == 404
            assert (await client.get("/openapi.json")).status_code == 404
    finally:
        get_settings.cache_clear()
