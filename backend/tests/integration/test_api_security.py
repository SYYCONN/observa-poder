import os
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from app.db import session as sessions


def test_http_query_timeout_cancels_statement_and_does_not_leak_to_pool(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Execute scripts/test_backend.py para PostgreSQL isolado.")
    engine = create_engine(url, pool_size=1, max_overflow=0)
    monkeypatch.setattr(sessions, "get_engine", lambda: engine)
    monkeypatch.setattr(sessions, "get_settings", lambda: SimpleNamespace(db_statement_timeout_ms=100))
    try:
        with engine.connect() as connection:
            original = connection.scalar(text("SHOW statement_timeout"))
        generator = sessions.get_db()
        session = next(generator)
        try:
            assert session.scalar(text("SHOW statement_timeout")) == "100ms"
            with pytest.raises(DBAPIError) as error:
                session.execute(text("SELECT pg_sleep(1)"))
            assert error.value.orig.sqlstate == "57014"
        finally:
            generator.close()
        with engine.connect() as connection:
            assert connection.scalar(text("SHOW statement_timeout")) == original
    finally:
        engine.dispose()
