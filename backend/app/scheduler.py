"""Processo de coleta automática das fontes oficiais.

Executado como um serviço separado do processo HTTP para que a API continue
responsiva enquanto uma coleta consulta e normaliza os dados da Câmara.
"""

import logging
import time
from collections.abc import Callable

from sqlalchemy.engine import Engine

from app.core.config import get_settings
from app.core.dates import local_today
from app.db.session import get_engine
from app.jobs.import_deputies import import_deputies
from app.jobs.import_camara_deputy_profiles import import_camara_deputy_profiles
from app.jobs.import_election_results import import_election_results
from app.jobs.import_legislation import import_legislation
from app.jobs.import_senators import import_senators
from app.jobs.import_senado_legislation import import_senado_legislation
from app.jobs.import_camara_expenses import import_camara_expenses
from app.jobs.import_camara_remuneration import import_camara_remuneration
from app.jobs.import_camara_staff import import_camara_staff
from app.jobs.import_portal_amendments_open_data import import_portal_amendments_open_data
from app.jobs.import_camara_votes import import_camara_votes
from app.jobs.generate_citizen_explanations import generate_citizen_explanations

logger = logging.getLogger("de_olho.scheduler")


def run_job(name: str, job: Callable[[], dict]) -> None:
    started = time.monotonic()
    try:
        job()
    except Exception as exc:
        logger.error("Coleta automática falhou: %s (%s)", name, type(exc).__name__)
    else:
        logger.info(
            "Coleta automática concluída: %s (%.1fs)", name, time.monotonic() - started
        )


def current_competence() -> dict[str, int]:
    today = local_today()
    return {"year": today.year, "month": today.month}


def run_forever() -> None:
    settings = get_settings()
    if not settings.scheduler_enabled:
        logger.info("Agendador desabilitado por SCHEDULER_ENABLED=false")
        return

    engine = get_engine()
    jobs: list[tuple[str, Callable[[Engine], dict], int]] = [
        (
            "camara.current_deputies",
            import_deputies,
            settings.deputies_import_interval_minutes * 60,
        ),
        (
            "senado.current_senators",
            import_senators,
            settings.senators_import_interval_minutes * 60,
        ),
        (
            "senado.recent_legislation",
            import_senado_legislation,
            settings.senate_legislation_import_interval_minutes * 60,
        ),
        (
            "camara.recent_legislation",
            import_legislation,
            settings.legislation_import_interval_minutes * 60,
        ),
    ]
    if settings.citizen_explanation_provider != "disabled":
        jobs.append(
            (
                "automation.citizen_explanations",
                lambda current_engine: generate_citizen_explanations(
                    current_engine,
                    batch_size=settings.citizen_explanation_batch_size,
                ),
                settings.citizen_explanation_interval_minutes * 60,
            )
        )
    if settings.election_results_import_enabled:
        jobs.append(
            (
                "tse.election_results",
                lambda current_engine: import_election_results(
                    current_engine, year=settings.election_results_year
                ),
                settings.election_results_import_interval_minutes * 60,
            )
        )
    if settings.deputy_profiles_import_enabled:
        jobs.append(
            (
                "camara.deputy_profiles",
                import_camara_deputy_profiles,
                settings.deputy_profiles_import_interval_minutes * 60,
            )
        )
    if settings.camara_expenses_import_enabled:
        jobs.append(
            (
                "camara.parliamentary_expenses",
                lambda current_engine: import_camara_expenses(
                    current_engine, year=settings.camara_expenses_year
                ),
                settings.camara_expenses_import_interval_minutes * 60,
            )
        )
    if settings.camara_remuneration_import_enabled:
        jobs.append(
            (
                "camara.parliamentary_remuneration",
                lambda current_engine: import_camara_remuneration(
                    current_engine,
                    **current_competence(),
                ),
                settings.camara_remuneration_import_interval_minutes * 60,
            )
        )
    if settings.camara_staff_import_enabled:
        jobs.append(
            (
                "camara.parliamentary_staff",
                lambda current_engine: import_camara_staff(
                    current_engine,
                    **current_competence(),
                ),
                settings.camara_staff_import_interval_minutes * 60,
            )
        )
    if settings.portal_amendments_import_enabled:
        jobs.append(
            (
                "portal.parliamentary_amendments_open_data",
                lambda current_engine: import_portal_amendments_open_data(
                    current_engine,
                    year=settings.portal_amendments_year,
                ),
                settings.portal_amendments_import_interval_minutes * 60,
            )
        )
    if settings.camara_votes_import_enabled:
        jobs.append(
            (
                "camara.annual_votes",
                lambda current_engine: import_camara_votes(
                    current_engine, year=settings.camara_votes_year
                ),
                settings.camara_votes_import_interval_minutes * 60,
            )
        )
    next_run = {name: 0.0 for name, _, _ in jobs}
    logger.info(
        "Agendador iniciado; deputados a cada %sm, senadores a cada %sm, legislação Senado a cada %sm, legislação Câmara a cada %sm",
        settings.deputies_import_interval_minutes,
        settings.senators_import_interval_minutes,
        settings.senate_legislation_import_interval_minutes,
        settings.legislation_import_interval_minutes,
    )

    if not settings.scheduler_run_on_startup:
        now = time.monotonic()
        next_run = {name: now + interval for name, _, interval in jobs}

    while True:
        for name, job, interval in jobs:
            if time.monotonic() < next_run[name]:
                continue
            run_job(name, lambda job=job: job(engine))
            next_run[name] = time.monotonic() + interval
        time.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    run_forever()
