"""Limites operacionais, competência e atualização restrita do ambiente externo."""

from datetime import date
import importlib.util
from pathlib import Path

import httpx
import pytest

from app import scheduler
from app.core import collector_http
from app.core.config import Settings


@pytest.mark.parametrize("today, expected", [
    (date(2026, 11, 17), {"year": 2026, "month": 10}),
    (date(2027, 1, 1), {"year": 2026, "month": 12}),
    (date(2028, 3, 1), {"year": 2028, "month": 2}),
])
def test_remuneration_uses_last_completed_month(monkeypatch, today, expected):
    monkeypatch.setattr(scheduler, "local_today", lambda: today)
    assert scheduler.remuneration_competence() == expected


def test_public_html_requests_are_paced(monkeypatch):
    clock = [0.0]
    delays = []
    monkeypatch.setattr(collector_http.time, "monotonic", lambda: clock[0])
    def sleep(delay):
        delays.append(delay)
        clock[0] += delay
    monkeypatch.setattr(collector_http.time, "sleep", sleep)
    with collector_http.public_html_client() as client:
        hook = client.event_hooks["request"][0]
        for _ in range(3):
            hook(httpx.Request("GET", "https://www.camara.leg.br/"))
    assert delays == [1, 1]


def test_annual_collectors_follow_year_rollover(monkeypatch):
    settings = Settings(
        _env_file=None, db_password="test-only", app_env="test",
        scheduler_run_on_startup=True, citizen_explanation_enabled=False,
        deputy_profiles_import_enabled=False, camara_remuneration_import_enabled=False,
        camara_staff_import_enabled=False, election_results_import_enabled=False,
        camara_expenses_import_enabled=True, camara_expenses_year=0,
        portal_amendments_import_enabled=True, portal_amendments_year=0,
        camara_votes_import_enabled=True, camara_votes_year=0,
    )
    monkeypatch.setattr(scheduler, "get_settings", lambda: settings)
    monkeypatch.setattr(scheduler, "get_engine", lambda: object())
    monkeypatch.setattr(scheduler, "local_today", lambda: date(2027, 1, 1))
    for name in ["import_deputies", "import_senators", "import_legislation", "import_senado_legislation"]:
        monkeypatch.setattr(scheduler, name, lambda engine: {})
    years = []
    for name in ["import_camara_expenses", "import_camara_votes", "import_portal_amendments_open_data"]:
        monkeypatch.setattr(scheduler, name, lambda engine, year: years.append(year) or {})
    class EndCycle(BaseException):
        pass
    def sleep(seconds):
        raise EndCycle
    monkeypatch.setattr(scheduler.time, "sleep", sleep)
    with pytest.raises(EndCycle):
        scheduler.run_forever()
    assert years == [2027, 2027, 2027]


def test_configuration_preserves_other_values_and_is_idempotent(tmp_path):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("configure_collectors", root / "scripts/configure_collectors.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    env = tmp_path / "production.env"
    env.write_text("# preserve\nSOME_PRIVATE_OPTION=fixture-only\nOBSERVA_HOST=example.org\nOBSERVA_COLLECT_VOTES=false\nOBSERVA_COLLECT_VOTES=false\n")
    module.configure(env)
    result = env.read_text()
    assert "SOME_PRIVATE_OPTION=fixture-only\nOBSERVA_HOST=example.org" in result
    assert result.count("OBSERVA_COLLECT_VOTES=") == 1
    assert all(f"{key}=true" in result for key in module.OPTIONS)
    assert env.stat().st_mode & 0o777 == 0o600
    module.configure(env)
    assert env.read_text() == result
