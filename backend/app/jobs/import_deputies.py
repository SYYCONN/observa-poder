"""Coleta manual: python -m app.jobs.import_deputies. Não executa no startup da API."""

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.integrations.camara.client import CamaraClient, SourceError
from app.modules.coletas.models import ImportRun
from app.modules.parlamentares.models import Parliamentarian
from app.modules.parlamentares.service import persist_deputies

JOB = "camara.current_deputies"
LOCK_KEY = 2810202601


class ImportBusy(Exception):
    pass


class ImportFailed(Exception):
    def __init__(self, run_id, code):
        self.run_id = run_id
        self.code = code
        super().__init__(f"Importação {run_id} falhou ({code}); consulte import_runs.")


def utc_now():
    return datetime.now(timezone.utc)


def import_deputies(engine, client=None):
    client = client or CamaraClient()
    run_id = uuid4()
    try:
        with engine.connect() as lock:
            acquired = lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY})
            lock.commit()
            if not acquired:
                raise ImportBusy("Já existe uma importação de deputados em execução.")
            try:
                with Session(engine) as session, session.begin():
                    # Só reclassificar execuções abandonadas depois de obter o lock exclusivo.
                    session.execute(
                        update(ImportRun)
                        .where(
                            ImportRun.job == JOB,
                            ImportRun.status == "running",
                        )
                        .values(
                            status="interrupted",
                            finished_at=utc_now(),
                            error_code="interrupted",
                            error_message="Execução anterior interrompida; coleta será reiniciada integralmente.",
                        )
                    )
                    session.add(
                        ImportRun(id=run_id, job=JOB, status="running", started_at=utc_now())
                    )
                try:
                    deputies = client.fetch_current_deputies()
                    if not deputies:
                        raise SourceError("Lista vazia; coleta não publicada.")
                    with Session(engine) as session, session.begin():
                        # A lista oficial representa a fotografia atual. Registros ausentes
                        # continuam preservados, mas deixam de ser apresentados como atuais.
                        session.execute(
                            update(Parliamentarian)
                            .where(Parliamentarian.source == "camara")
                            .values(is_current=False)
                        )
                        previous = session.scalar(
                            select(ImportRun)
                            .where(
                                ImportRun.job == JOB,
                                ImportRun.status == "success",
                            )
                            .order_by(ImportRun.finished_at.desc())
                            .limit(1)
                        )
                        if previous and len(deputies) < previous.received * 0.7:
                            raise SourceError(
                                "Queda superior a 30% em relação à última coleta; investigar a fonte."
                            )
                        run = session.get(ImportRun, run_id)
                        counts = persist_deputies(session, deputies, run_id, utc_now())
                        run.status = "success"
                        run.finished_at = utc_now()
                        run.pages = client.pages
                        run.received = len(deputies)
                        for key, value in counts.items():
                            setattr(run, key, value)
                    return {
                        "run_id": str(run_id),
                        "status": "success",
                        "pages": client.pages,
                        "received": len(deputies),
                        **counts,
                    }
                except Exception as exc:
                    code = "source_error" if isinstance(exc, SourceError) else "processing_error"
                    message = (
                        str(exc)
                        if isinstance(exc, SourceError)
                        else "Erro interno; publicação revertida. Verificar serviço e schema do banco."
                    )
                    with Session(engine) as session, session.begin():
                        run = session.get(ImportRun, run_id)
                        run.status = "failed"
                        run.finished_at = utc_now()
                        run.pages = client.pages
                        run.received = client.received
                        run.error_code = code
                        run.error_message = message[:500]
                    raise ImportFailed(run_id, code) from None
            finally:
                lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY})
                lock.commit()
    finally:
        client.close()


def main():
    try:
        print(json.dumps(import_deputies(get_engine()), ensure_ascii=False))
    except (ImportBusy, ImportFailed) as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
