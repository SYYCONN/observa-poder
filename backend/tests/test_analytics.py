from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.session import get_db
from app.main import create_app
from app.modules.analytics import service
from app.modules.analytics.models import DailyMetric
from app.modules.coletas.models import ImportRun
from app.api.routes import analytics

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "test-only")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ANALYTICS_ENABLED", "true")
    monkeypatch.setenv("ANALYTICS_ADMIN_TOKEN", "test-admin-token")
    get_settings.cache_clear()
    app = create_app()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    DailyMetric.__table__.create(engine)
    ImportRun.__table__.create(engine)
    def database():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[get_db] = database
    monkeypatch.setattr(service, "get_engine", lambda: engine)
    monkeypatch.setattr(service, "local_today", lambda: date(2026, 11, 3))
    monkeypatch.setattr(analytics, "local_today", lambda: date(2026, 11, 3))
    @app.get("/api/v1/parliamentarians/test/{person_id}.pdf")
    def fake_download(person_id: str):
        return {"ok": True}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    engine.dispose()
    get_settings.cache_clear()


async def test_summary_requires_bearer_and_is_not_cached(client):
    assert (await client.get("/api/v1/analytics/summary")).status_code == 401
    assert (await client.get("/api/v1/analytics/summary", headers={"Authorization": "Bearer wrong"})).status_code == 401
    headers = {"Authorization": "Bearer test-admin-token"}
    response = await client.get("/api/v1/analytics/summary", headers=headers)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["timezone"] == "America/Sao_Paulo"
    assert response.json()["items"] == []
    assert (await client.get("/api/v1/analytics/summary?days=999", headers=headers)).status_code == 422


async def test_pageview_rejects_sensitive_dimensions_and_foreign_origin(client, monkeypatch):
    record = MagicMock()
    monkeypatch.setattr(analytics, "record", record)
    headers = {"Origin": "http://localhost:3000"}
    for payload in ({"route": "/deputados?search=private"},
                    {"route": "/parlamentares/person-id"},
                    {"route": "/deputados", "search": "private"}):
        assert (await client.post("/api/v1/analytics/pageviews", json=payload, headers=headers)).status_code == 422
    assert (await client.post("/api/v1/analytics/pageviews", json={"route": "/"})).status_code == 403
    record.assert_not_called()
    assert (await client.post("/api/v1/analytics/pageviews", json={"route": "/parlamentares/[id]"}, headers=headers)).status_code == 204
    record.assert_called_once_with("pageview", "/parlamentares/[id]")


async def test_privacy_signals_and_disabled_collection(client, monkeypatch):
    record = MagicMock()
    monkeypatch.setattr(analytics, "record", record)
    for signal in ("DNT", "Sec-GPC"):
        response = await client.post("/api/v1/analytics/pageviews", json={"route": "/"}, headers={"Origin": "http://localhost:3000", signal: "1"})
        assert response.status_code == 204
    record.assert_not_called()
    monkeypatch.setenv("ANALYTICS_ENABLED", "false")
    get_settings.cache_clear()
    assert (await client.post("/api/v1/analytics/pageviews", json={"route": "/"})).status_code == 404
    assert (await client.get("/api/v1/analytics/summary")).status_code == 404


async def test_atomic_aggregation_and_retention(client):
    service.record("pageview", "/")
    service.record("pageview", "/")
    with Session(service.get_engine()) as db:
        db.add(DailyMetric(day=date(2026, 8, 5), category="pageview", route="/", outcome="ok", count=4, duration_ms=0))
        db.add(DailyMetric(day=date(2026, 8, 6), category="pageview", route="/", outcome="ok", count=1, duration_ms=0))
        db.commit()
    assert service.purge() == 1
    response = await client.get("/api/v1/analytics/summary", headers={"Authorization": "Bearer test-admin-token"})
    assert response.json()["items"][0]["count"] == 2


@pytest.mark.parametrize("query", ["search=private&state=secret", "q=private&date_from=secret"])
async def test_middleware_stores_template_and_never_values(client, monkeypatch, query):
    from app.modules.analytics import middleware
    record = MagicMock()
    monkeypatch.setattr(middleware, "record", record)
    await client.get(f"/api/v1/parliamentarians/test/private-id.pdf?{query}")
    serialized = str(record.call_args_list)
    assert "private" not in serialized and "secret" not in serialized
    assert "search_request" in serialized and "filter_request" in serialized
    assert "download" in serialized and "{person_id}" in serialized
    record.reset_mock()
    await client.get("/api/v1/unknown/private")
    record.assert_not_called()


async def test_storage_failure_logs_no_database_details(client, monkeypatch, caplog):
    from sqlalchemy.exc import OperationalError
    engine = MagicMock(side_effect=OperationalError("secret-sql", {}, Exception("secret-host")))
    monkeypatch.setattr(service, "get_engine", engine)
    service.record("pageview", "/")
    assert "analytics_write_failed" in caplog.text
    assert "secret" not in caplog.text


async def test_summary_reports_integration_health_without_exporting_logs(client):
    now = datetime.now(UTC)
    job = "camara.current_deputies"
    with Session(service.get_engine()) as db:
        for status, days_ago in [("failed", 15), ("success", 10), ("interrupted", 2), ("failed", 1)]:
            finished = now - timedelta(days=days_ago)
            db.add(ImportRun(job=job, status=status, started_at=finished - timedelta(minutes=1),
                             finished_at=finished, error_message="sensitive log content"))
        db.add(ImportRun(job="unlisted-sensitive-job", status="success", started_at=now))
        db.commit()

    response = await client.get("/api/v1/analytics/summary", headers={"Authorization": "Bearer test-admin-token"})
    assert response.status_code == 200
    integrations = {item["job"]: item for item in response.json()["integrations"]}
    assert integrations[job]["latest_status"] == "failed"
    assert datetime.fromisoformat(integrations[job]["last_success_at"]).date() == (now - timedelta(days=10)).date()
    assert integrations[job]["failures_last_7_days"] == 2
    assert integrations["senado.current_senators"]["latest_status"] is None
    assert "sensitive" not in response.text
