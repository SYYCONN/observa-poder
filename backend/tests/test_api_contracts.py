"""Contratos HTTP sem rede externa; consultas inválidas não chegam ao banco."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.routes.legislation import proposition_label
from app.api.dependencies import database_session
from app.core.config import get_settings
from app.main import create_app
from app.modules.proposicoes.models import Proposition

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def api(monkeypatch):
    monkeypatch.setenv("DB_PASSWORD", "test-only")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    db = MagicMock()
    db.get.return_value = None
    app = create_app()
    app.dependency_overrides[database_session] = lambda: db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, db
    finally:
        app.dependency_overrides.clear()
        get_settings.cache_clear()


@pytest.mark.parametrize("route", ["parliamentarians", "propositions", "votings"])
@pytest.mark.parametrize(
    "params",
    [
        {"source": "unknown"},
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
    ],
)
async def test_invalid_list_query_is_rejected_before_database_access(api, route, params):
    client, db = api
    response = await client.get(f"/api/v1/{route}", params=params)
    assert response.status_code == 422
    assert response.json()["detail"]
    assert not db.mock_calls


async def test_invalid_parliamentarian_status_is_rejected_before_database_access(api):
    client, db = api
    response = await client.get("/api/v1/parliamentarians?status=unknown")
    assert response.status_code == 422
    assert not db.mock_calls


@pytest.mark.parametrize(
    "route",
    [
        "parliamentarians/not-a-uuid",
        "propositions/not-a-uuid",
        "votings/not-a-uuid",
    ],
)
async def test_invalid_identifier_does_not_query_database(api, route):
    client, db = api
    response = await client.get(f"/api/v1/{route}")
    assert response.status_code == 422
    assert not db.mock_calls


@pytest.mark.parametrize(
    ("route", "detail"),
    [
        ("parliamentarians/{id}", "Parlamentar não encontrado"),
        ("parliamentarians/{id}/financial-expenses", "Parlamentar não encontrado"),
        ("parliamentarians/{id}/staff", "Parlamentar não encontrado"),
        ("parliamentarians/{id}/authored-propositions", "Parlamentar não encontrado"),
        ("parliamentarians/{id}/votes", "Parlamentar não encontrado"),
        ("parliamentarians/{id}/amendments.csv", "Parlamentar não encontrado"),
        ("parliamentarians/{id}/amendments.pdf", "Parlamentar não encontrado"),
        ("parliamentarians/{id}/staff.pdf", "Parlamentar não encontrado"),
        ("propositions/{id}", "Proposição não encontrada"),
        ("votings/{id}", "Votação não encontrada"),
    ],
)
async def test_missing_record_returns_public_404(api, route, detail):
    client, db = api
    identifier = uuid4()
    response = await client.get("/api/v1/" + route.format(id=identifier))
    assert response.status_code == 404
    assert response.json() == {"detail": detail}
    assert db.get.call_args.args[1] == identifier


async def test_empty_parliamentarian_page_preserves_pagination(api):
    client, db = api
    db.scalar.return_value = 0
    db.execute.return_value = []
    response = await client.get("/api/v1/parliamentarians?source=senado&limit=7&offset=14")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "limit": 7, "offset": 14}


@pytest.mark.parametrize("route", ["propositions", "votings"])
async def test_empty_legislation_collection_is_an_array(api, route):
    client, db = api
    db.scalars.return_value.all.return_value = []
    response = await client.get(f"/api/v1/{route}?source=senado")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("route", ["propositions/search", "votings/search"])
async def test_empty_legislation_search_preserves_pagination_and_facets(api, route):
    client, db = api
    db.scalar.return_value = 0
    db.scalars.return_value.all.return_value = []
    response = await client.get(f"/api/v1/{route}?source=camara&limit=12&offset=24")
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 12,
        "offset": 24,
        "facets": {"years": [], "kinds" if route.startswith("propositions") else "modes": []},
    }


@pytest.mark.parametrize(
    ("route", "params"),
    [
        ("propositions/search", {"year": 1700}),
        ("propositions/search", {"order": "popular"}),
        ("votings/search", {"result": "draw"}),
        ("votings/search", {"mode": "secret"}),
    ],
)
async def test_invalid_legislation_search_is_rejected_before_database_access(api, route, params):
    client, db = api
    response = await client.get(f"/api/v1/{route}", params=params)
    assert response.status_code == 422
    assert not db.mock_calls


async def test_parties_route_is_not_interpreted_as_a_person_identifier(api):
    client, db = api
    db.execute.return_value.all.return_value = [("PT",), ("UNIÃO",)]
    response = await client.get("/api/v1/parliamentarians/parties?source=camara")
    assert response.status_code == 200
    assert response.json() == ["PT", "UNIÃO"]
    db.get.assert_not_called()


async def test_content_automation_monitor_is_hidden_without_configuration(api):
    client, db = api
    response = await client.get("/api/v1/content-admin/citizen-explanations")
    assert response.status_code == 404
    assert not db.mock_calls


async def test_content_automation_monitor_requires_its_own_token(api, monkeypatch):
    client, db = api
    monkeypatch.setenv("CONTENT_ADMIN_TOKEN", "content-test-token")
    get_settings.cache_clear()

    response = await client.get(
        "/api/v1/content-admin/citizen-explanations",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401
    assert not db.mock_calls

    db.scalar.return_value = 0
    db.execute.return_value.all.return_value = []
    response = await client.get(
        "/api/v1/content-admin/citizen-explanations",
        headers={"Authorization": "Bearer content-test-token"},
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 30,
        "offset": 0,
        "counts": {"generating": 0, "published": 0, "rejected": 0, "failed": 0},
    }


async def test_content_automation_monitor_has_no_manual_generation_endpoint(api, monkeypatch):
    client, db = api
    proposition_id = uuid4()
    monkeypatch.setenv("CONTENT_ADMIN_TOKEN", "content-test-token")
    get_settings.cache_clear()
    response = await client.post(
        f"/api/v1/content-admin/citizen-explanations/{proposition_id}/generate-draft",
        headers={"Authorization": "Bearer content-test-token"},
        json={},
    )
    assert response.status_code == 405
    db.commit.assert_not_called()


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("status", "reviewed"),
        ("limit", "0"),
        ("offset", "-1"),
    ],
)
async def test_content_automation_monitor_rejects_invalid_filters(
    api, monkeypatch, parameter, value
):
    client, db = api
    monkeypatch.setenv("CONTENT_ADMIN_TOKEN", "content-test-token")
    get_settings.cache_clear()
    response = await client.get(
        "/api/v1/content-admin/citizen-explanations",
        params={parameter: value},
        headers={"Authorization": "Bearer content-test-token"},
    )
    assert response.status_code == 422
    assert not db.mock_calls


@pytest.mark.parametrize(
    ("number", "year", "expected"),
    [
        (1, 2026, "PL 1/2026"),
        (1, None, "PL 1"),
        (None, 2026, "PL de 2026"),
        (None, None, "PL"),
    ],
)
def test_proposition_label_omits_empty_separators(number, year, expected):
    assert proposition_label(Proposition(kind="PL", number=number, year=year)) == expected
