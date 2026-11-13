"""Real PostgreSQL concurrency check, only against the isolated test database."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.modules.analytics import service
from app.modules.analytics.models import DailyMetric


def test_concurrent_increments_do_not_lose_events(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Execute scripts/test_backend.py para PostgreSQL isolado.")
    root = create_engine(url)
    schema = "test_" + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = root.execution_options(schema_translate_map={None: schema})
    try:
        DailyMetric.__table__.create(engine)
        monkeypatch.setattr(service, "get_engine", lambda: engine)
        monkeypatch.setattr(service, "local_today", lambda: date(2026, 11, 3))
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(lambda _: service.record("api_request", "/fixed/{id}", "200", 5), range(40)))
        with Session(engine) as db:
            row = db.scalar(select(DailyMetric))
            assert row.count == 40
            assert row.duration_ms == 200
    finally:
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()
