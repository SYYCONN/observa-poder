"""Importa a folha mensal de deputados publicada pela Câmara."""

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.dates import local_today
from app.db.session import get_engine
from app.integrations.camara.remuneration import (
    parse_remuneration_links,
    parse_remuneration_page,
    remuneration_list_url,
    remuneration_month_url,
)
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.financas.models import ParliamentaryRemuneration
from app.modules.parlamentares.models import Parliamentarian
from app.modules.proposicoes.linking import normalize_name

JOB = "camara.parliamentary_remuneration"
SOURCE = "camara"
LOCK_KEY = 2810302601
NORMALIZER_VERSION = "remuneration-v1"


def now():
    return datetime.now(timezone.utc)


def _match_person(name: str, people: list[tuple[str, object]]) -> object | None:
    """Aceita somente nome normalizado único; sem aproximação editorial."""

    normalized = normalize_name(name)
    exact = [
        person_id for person_name, person_id in people if normalize_name(person_name) == normalized
    ]
    return exact[0] if len(exact) == 1 else None


def import_camara_remuneration(engine, year: int, month: int, client=None):
    owns_client = client is None
    client = client or httpx.Client(
        timeout=httpx.Timeout(30, connect=10),
        follow_redirects=True,
        headers={"Accept": "text/html", "User-Agent": "DeOlhoNaPolitica/0.1"},
    )
    run_id = uuid4()
    started = now()
    try:
        with engine.connect() as lock:
            if not lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}):
                raise RuntimeError("Já existe uma importação de remuneração em execução.")
            lock.commit()
            try:
                with Session(engine) as session, session.begin():
                    session.add(ImportRun(id=run_id, job=JOB, status="running", started_at=started))

                with Session(engine) as session:
                    people = list(
                        session.execute(
                            select(Parliamentarian.name, Parliamentarian.id).where(
                                Parliamentarian.source == SOURCE
                            )
                        )
                    )
                links: list[tuple[str, str]] = []
                for page in range(1, 40):
                    response = client.get(remuneration_list_url(page))
                    response.raise_for_status()
                    page_links = parse_remuneration_links(response.text)
                    if not page_links:
                        break
                    links.extend(page_links)
                    if len(page_links) < 20:
                        break
                if not links:
                    raise RuntimeError("A fonte não publicou a lista de remuneração.")

                seen = now()
                payload_metadata = {"year": year, "month": month, "people": len(links)}
                digest = hashlib.sha256(
                    json.dumps(payload_metadata, sort_keys=True).encode("utf-8")
                ).hexdigest()
                source_url = remuneration_list_url(1)
                with Session(engine) as session, session.begin():
                    source_record = session.scalar(
                        select(SourceRecord).where(
                            SourceRecord.source == SOURCE,
                            SourceRecord.entity == "parliamentary_remuneration",
                            SourceRecord.external_id == f"{year}-{month:02d}",
                            SourceRecord.payload_hash == digest,
                            SourceRecord.normalizer_version == NORMALIZER_VERSION,
                        )
                    )
                    if source_record is None:
                        source_record = SourceRecord(
                            source=SOURCE,
                            entity="parliamentary_remuneration",
                            external_id=f"{year}-{month:02d}",
                            source_url=source_url,
                            payload_hash=digest,
                            normalizer_version=NORMALIZER_VERSION,
                            payload=payload_metadata,
                            first_seen_at=seen,
                            last_seen_at=seen,
                            last_run_id=run_id,
                        )
                        session.add(source_record)
                        session.flush()
                    else:
                        source_record.last_seen_at = seen
                        source_record.last_run_id = run_id

                    existing = {
                        (row.parliamentarian_id, row.year, row.month): row
                        for row in session.scalars(
                            select(ParliamentaryRemuneration).where(
                                ParliamentaryRemuneration.source == SOURCE,
                                ParliamentaryRemuneration.year == year,
                                ParliamentaryRemuneration.month == month,
                            )
                        )
                    }
                    inserted = updated = skipped = 0
                    for name, base_url in links:
                        person_id = _match_person(name, people)
                        if person_id is None:
                            skipped += 1
                            continue
                        detail_url = remuneration_month_url(base_url, year, month)
                        detail = client.get(detail_url)
                        detail.raise_for_status()
                        parsed = parse_remuneration_page(detail.text)
                        if parsed["fixed_amount"] is None and parsed["net_amount"] is None:
                            skipped += 1
                            continue
                        key = (person_id, year, month)
                        row = existing.get(key)
                        if row is None:
                            row = ParliamentaryRemuneration(
                                parliamentarian_id=person_id,
                                source=SOURCE,
                                year=year,
                                month=month,
                                payroll_type="folha_normal",
                            )
                            session.add(row)
                            existing[key] = row
                            inserted += 1
                        else:
                            updated += 1
                        row.fixed_amount = parsed["fixed_amount"]
                        row.net_amount = parsed["net_amount"]
                        row.source_document_url = detail_url
                        row.source_url = source_url
                        row.collected_at = seen
                        row.source_record_id = source_record.id
                    run = session.get(ImportRun, run_id)
                    run.status = "success"
                    run.finished_at = now()
                    run.received = len(links)
                    run.inserted = inserted
                    run.updated = updated
                    run.unchanged = max(len(links) - skipped - inserted - updated, 0)
                    run.pages = (len(links) + 19) // 20
                return {
                    "run_id": str(run_id),
                    "status": "success",
                    "year": year,
                    "month": month,
                    "received": len(links),
                    "inserted": inserted,
                    "updated": updated,
                    "skipped": skipped,
                }
            except Exception as exc:
                with Session(engine) as session, session.begin():
                    run = session.get(ImportRun, run_id)
                    if run:
                        run.status = "failed"
                        run.finished_at = now()
                        run.error_code = "processing_error"
                        run.error_message = type(exc).__name__
                raise
            finally:
                lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY})
                lock.commit()
    finally:
        if owns_client:
            client.close()


def main():
    today = local_today()
    result = import_camara_remuneration(get_engine(), today.year, today.month)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
