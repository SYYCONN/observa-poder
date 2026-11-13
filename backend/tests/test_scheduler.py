"""Agendamento validado sem banco ou consultas às fontes oficiais."""

from datetime import date
from importlib import import_module
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app import scheduler
from app.core.config import Settings


INTERVALS = [name for name in Settings.model_fields if name.endswith("_import_interval_minutes")]
JOB_MODULES = [
    "import_deputies", "import_camara_deputy_profiles", "import_senators", "import_legislation", "import_senado_legislation",
    "import_election_results", "import_camara_expenses", "import_camara_votes",
    "import_camara_remuneration", "import_camara_staff", "import_portal_amendments",
    "import_portal_amendments_open_data",
]


@pytest.mark.parametrize("field", INTERVALS)
@pytest.mark.parametrize("value", [0, -1])
def test_invalid_interval_is_rejected(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, db_password="test-only", **{field: value})


@pytest.mark.parametrize("value", [-0.1, float("inf"), float("nan")])
def test_invalid_request_delay_is_rejected(value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, db_password="test-only", portal_amendments_request_interval_seconds=value)


def test_independent_collectors_have_distinct_locks():
    keys = [import_module(f"app.jobs.{name}").LOCK_KEY for name in JOB_MODULES]
    assert len(set(keys)) == len(keys)


def test_fresh_imports_and_api_creation_do_not_collect():
    # Processo novo: módulos já carregados pelo pytest não podem ocultar efeitos de import.
    code = """
import importlib
import pkgutil
from unittest.mock import patch
import app

with patch('sqlalchemy.create_engine', side_effect=AssertionError('unexpected database')), \\
     patch('httpx.Client.send', side_effect=AssertionError('unexpected HTTP')), \\
     patch('socket.create_connection', side_effect=AssertionError('unexpected network')):
    for module in pkgutil.walk_packages(app.__path__, app.__name__ + '.'):
        importlib.import_module(module.name)
    from app.main import create_app
    create_app()
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "DB_PASSWORD": "test-only", "APP_ENV": "test", "ANALYTICS_ENABLED": "false"},
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr


def test_disabled_scheduler_does_not_open_database(monkeypatch):
    monkeypatch.setattr(scheduler, "get_settings", lambda: Settings(
        _env_file=None, db_password="test-only", scheduler_enabled=False,
    ))
    engine = Mock(side_effect=AssertionError("Database must remain untouched"))
    monkeypatch.setattr(scheduler, "get_engine", engine)
    scheduler.run_forever()
    engine.assert_not_called()


def test_month_and_year_use_same_business_date(monkeypatch):
    clock = Mock(side_effect=[date(2026, 12, 31), date(2027, 1, 1)])
    monkeypatch.setattr(scheduler, "local_today", clock)
    assert scheduler.current_competence() == {"year": 2026, "month": 12}
    clock.assert_called_once()


def test_failed_job_does_not_prevent_next_job(caplog):
    failed = Mock(side_effect=RuntimeError("source unavailable"))
    following = Mock(return_value={"status": "success"})
    scheduler.run_job("failed", failed)
    scheduler.run_job("following", following)
    following.assert_called_once()
    assert "Coleta automática falhou: failed" in caplog.text


class EndCycle(BaseException):
    pass


@pytest.mark.parametrize("on_startup", [True, False])
def test_startup_policy_and_deadlines_after_slow_job(monkeypatch, on_startup):
    settings = Settings(
        _env_file=None, db_password="test-only", scheduler_run_on_startup=on_startup,
        deputies_import_interval_minutes=1, senators_import_interval_minutes=2,
        senate_legislation_import_interval_minutes=1, legislation_import_interval_minutes=1,
        election_results_import_enabled=False, camara_expenses_import_enabled=False,
        deputy_profiles_import_enabled=False,
        camara_remuneration_import_enabled=False, camara_staff_import_enabled=False,
        portal_amendments_import_enabled=False, camara_votes_import_enabled=False,
    )
    monkeypatch.setattr(scheduler, "get_settings", lambda: settings)
    engine = object()
    monkeypatch.setattr(scheduler, "get_engine", lambda: engine)
    now = [100.0]
    monkeypatch.setattr(scheduler.time, "monotonic", lambda: now[0])
    calls = []

    def deputies(db):
        assert db is engine
        calls.append("deputies")
        now[0] += 70
        return {}

    monkeypatch.setattr(scheduler, "import_deputies", deputies)
    for name in ["import_senators", "import_senado_legislation", "import_legislation"]:
        monkeypatch.setattr(scheduler, name, lambda db, name=name: calls.append(name) or {})

    def sleep(seconds):
        if not on_startup and not calls:
            now[0] += 60
            return
        raise EndCycle

    monkeypatch.setattr(scheduler.time, "sleep", sleep)
    with pytest.raises(EndCycle):
        scheduler.run_forever()
    assert calls == ["deputies", "import_senators", "import_senado_legislation", "import_legislation"]
