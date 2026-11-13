from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        pool_timeout=5,
        hide_parameters=True,
        connect_args={"connect_timeout": 3},
    )


def get_db():
    with Session(get_engine()) as session:
        # Transaction-local: collectors and subsequent pool users keep their own settings.
        session.execute(
            text("SELECT set_config('statement_timeout', :timeout, true)"),
            {"timeout": str(get_settings().db_statement_timeout_ms)},
        )
        yield session
