from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.modules.coletas.models import ImportRun

INTEGRATIONS = {
    "camara.current_deputies": "Câmara · deputados em exercício",
    "camara.deputy_profiles": "Câmara · perfis de deputados",
    "camara.deputy_history_supplement": "Câmara · complemento do histórico",
    "camara.recent_legislation": "Câmara · proposições e votações recentes",
    "camara.annual_votes": "Câmara · votos nominais anuais",
    "camara.parliamentary_expenses": "Câmara · despesas parlamentares",
    "camara.parliamentary_remuneration": "Câmara · remuneração parlamentar",
    "camara.parliamentary_staff": "Câmara · equipes parlamentares",
    "senado.current_senators": "Senado · senadores em exercício",
    "senado.recent_legislation": "Senado · matérias e votações recentes",
    "portal.parliamentary_amendments_open_data": "Portal da Transparência · emendas (arquivo)",
    "portal.parliamentary_amendments": "Portal da Transparência · emendas (API)",
    "tse.election_results": "TSE · resultados eleitorais",
}


class IntegrationHealth(BaseModel):
    job: str
    label: str
    latest_status: Literal["running", "success", "failed", "interrupted"] | None = None
    latest_started_at: datetime | None = None
    last_success_at: datetime | None = None
    failures_last_7_days: int = 0


def integration_health(db: Session) -> list[IntegrationHealth]:
    since = datetime.now(UTC) - timedelta(days=7)
    runs = (
        select(
            ImportRun.job,
            ImportRun.status,
            ImportRun.started_at,
            func.row_number()
            .over(partition_by=ImportRun.job, order_by=(ImportRun.started_at.desc(), ImportRun.id))
            .label("position"),
            func.max(case((ImportRun.status == "success", ImportRun.finished_at)))
            .over(partition_by=ImportRun.job)
            .label("last_success_at"),
            func.count()
            .filter(ImportRun.status.in_(("failed", "interrupted")), ImportRun.finished_at >= since)
            .over(partition_by=ImportRun.job)
            .label("failures_last_7_days"),
        )
        .where(ImportRun.job.in_(INTEGRATIONS))
        .subquery()
    )
    latest = {
        row.job: IntegrationHealth(
            job=row.job,
            label=INTEGRATIONS[row.job],
            latest_status=row.status,
            latest_started_at=row.started_at,
            last_success_at=row.last_success_at,
            failures_last_7_days=row.failures_last_7_days,
        )
        for row in db.execute(select(runs).where(runs.c.position == 1))
    }
    return [latest[job] if job in latest else IntegrationHealth(job=job, label=label)
            for job, label in INTEGRATIONS.items()]
