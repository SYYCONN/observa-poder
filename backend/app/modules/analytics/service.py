"""Only fixed dimensions reach storage. Never persist request URLs or headers."""
import logging
from datetime import timedelta

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dates import local_today
from app.db.session import get_engine
from app.modules.analytics.models import DailyMetric

logger = logging.getLogger(__name__)
PAGE_ROUTES = frozenset({
    "/", "/deputados", "/senadores", "/governadores", "/partidos", "/projetos",
    "/votacoes", "/parlamentares/[id]", "/proposicoes/[id]", "/votacoes/[id]",
})


def record(category: str, route: str, outcome: str = "ok", duration_ms: int = 0) -> None:
    statement = insert(DailyMetric).values(
        day=local_today(), category=category, route=route, outcome=outcome,
        count=1, duration_ms=max(0, duration_ms),
    )
    statement = statement.on_conflict_do_update(
        index_elements=["day", "category", "route", "outcome"],
        set_={"count": DailyMetric.count + 1,
              "duration_ms": DailyMetric.duration_ms + statement.excluded.duration_ms},
    )
    try:
        with Session(get_engine()) as session:
            session.execute(statement)
            session.commit()
    except SQLAlchemyError:
        # No exception details: database connection messages can contain secrets.
        logger.warning("analytics_write_failed")


def purge() -> int:
    """Run explicitly as a job; the retention window includes today."""
    cutoff = local_today() - timedelta(days=get_settings().analytics_retention_days - 1)
    with Session(get_engine()) as session:
        result = session.execute(delete(DailyMetric).where(DailyMetric.day < cutoff))
        session.commit()
        return result.rowcount
