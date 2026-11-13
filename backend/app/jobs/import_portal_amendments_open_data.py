"""Importa resumos de emendas a partir do arquivo aberto oficial do Portal."""

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import httpx

from app.integrations.download import download_bytes
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.dates import local_today
from app.db.session import get_engine
from app.integrations.portal_transparencia.open_data import (
    PORTAL_AMENDMENTS_ARCHIVE_URL,
    PORTAL_AMENDMENTS_OPEN_DATA_URL,
    PORTAL_AMENDMENTS_SOURCE_URL,
    group_open_data_amendments,
    normalize_author_name,
)
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.financas.models import ParliamentaryAmendment, ParliamentaryAmendmentSummary
from app.modules.parlamentares.models import Parliamentarian

JOB = "portal.parliamentary_amendments_open_data"
SOURCE = "portal_transparencia"
LOCK_KEY = 2810302608
NORMALIZER_VERSION = "portal-amendments-open-data-v1"


def now():
    return datetime.now(timezone.utc)


def _sum(values: list[Decimal | None]) -> Decimal | None:
    if not values or any(value is None for value in values):
        return None
    return sum(values, Decimal("0"))


def _unique_people_by_name(people) -> dict[str, object]:
    """Mapeia apenas nomes que identificam uma única pessoa entre as bases locais."""

    candidates: dict[str, list[object]] = {}
    for person_id, person_name in people:
        key = normalize_author_name(person_name)
        if key:
            candidates.setdefault(key, []).append(person_id)
    return {key: ids[0] for key, ids in candidates.items() if len(ids) == 1}


def import_portal_amendments_open_data(
    engine,
    year: int,
    client=None,
    archive_url: str = PORTAL_AMENDMENTS_ARCHIVE_URL,
):
    """Baixa o ZIP público e grava um resumo anual por parlamentar."""

    owns_client = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(120, connect=15), follow_redirects=True)
    run_id = uuid4()
    started = now()
    try:
        with engine.connect() as lock:
            if not lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}):
                raise RuntimeError("Já existe uma importação de emendas em execução.")
            lock.commit()
            try:
                with Session(engine) as session, session.begin():
                    session.add(ImportRun(id=run_id, job=JOB, status="running", started_at=started))

                content = download_bytes(client, archive_url, max_bytes=64 * 1024**2)
                grouped = group_open_data_amendments(content, year)
                source_metadata = {
                    "year": year,
                    "archive_url": archive_url,
                    "open_data_page": PORTAL_AMENDMENTS_OPEN_DATA_URL,
                    "matched_authors_in_file": len(grouped),
                    "amendments_in_file": sum(len(items) for items in grouped.values()),
                    "archive_sha256": hashlib.sha256(content).hexdigest(),
                }
                digest = source_metadata["archive_sha256"]
                collected_at = now()

                with Session(engine) as session, session.begin():
                    people = list(
                        session.execute(
                            select(Parliamentarian.id, Parliamentarian.name).where(
                                Parliamentarian.source.in_(["camara", "senado"])
                            )
                        )
                    )
                    people_by_name = _unique_people_by_name(people)
                    source_record = session.scalar(
                        select(SourceRecord).where(
                            SourceRecord.source == SOURCE,
                            SourceRecord.entity == "parliamentary_amendments_open_data",
                            SourceRecord.external_id == str(year),
                            SourceRecord.payload_hash == digest,
                            SourceRecord.normalizer_version == NORMALIZER_VERSION,
                        )
                    )
                    if source_record is None:
                        source_record = SourceRecord(
                            source=SOURCE,
                            entity="parliamentary_amendments_open_data",
                            external_id=str(year),
                            source_url=PORTAL_AMENDMENTS_OPEN_DATA_URL,
                            payload_hash=digest,
                            normalizer_version=NORMALIZER_VERSION,
                            payload=source_metadata,
                            first_seen_at=collected_at,
                            last_seen_at=collected_at,
                            last_run_id=run_id,
                        )
                        session.add(source_record)
                        session.flush()
                    else:
                        source_record.last_seen_at = collected_at
                        source_record.last_run_id = run_id
                        source_record.payload = source_metadata

                    existing = {
                        row.parliamentarian_id: row
                        for row in session.scalars(
                            select(ParliamentaryAmendmentSummary).where(
                                ParliamentaryAmendmentSummary.source == SOURCE,
                                ParliamentaryAmendmentSummary.year == year,
                            )
                        )
                    }
                    existing_details = {
                        (row.parliamentarian_id, row.external_id): row
                        for row in session.scalars(
                            select(ParliamentaryAmendment).where(
                                ParliamentaryAmendment.source == SOURCE,
                                ParliamentaryAmendment.year == year,
                            )
                        )
                    }
                    matched = 0
                    inserted = updated = skipped = 0
                    for author_name, records in grouped.items():
                        person_id = people_by_name.get(author_name)
                        if person_id is None:
                            skipped += 1
                            continue
                        if not records:
                            skipped += 1
                            continue
                        matched += 1
                        row = existing.get(person_id)
                        if row is None:
                            row = ParliamentaryAmendmentSummary(
                                parliamentarian_id=person_id,
                                source=SOURCE,
                                year=year,
                                amendment_count=0,
                                source_query_url=f"{PORTAL_AMENDMENTS_SOURCE_URL}?ano={year}",
                            )
                            session.add(row)
                            existing[person_id] = row
                            inserted += 1
                        else:
                            updated += 1
                        row.amendment_count = len(records)
                        row.committed_amount = _sum([item.committed for item in records.values()])
                        row.liquidated_amount = _sum([item.liquidated for item in records.values()])
                        row.paid_amount = _sum([item.paid for item in records.values()])
                        row.source_query_url = f"{PORTAL_AMENDMENTS_SOURCE_URL}?ano={year}"
                        row.source_url = PORTAL_AMENDMENTS_OPEN_DATA_URL
                        row.collected_at = collected_at
                        row.source_record_id = source_record.id

                        for item in records.values():
                            detail = existing_details.get((person_id, item.code))
                            if detail is None:
                                detail = ParliamentaryAmendment(
                                    external_id=item.code,
                                    parliamentarian_id=person_id,
                                    year=year,
                                )
                                session.add(detail)
                                existing_details[(person_id, item.code)] = detail
                            detail.amendment_type = item.amendment_type
                            detail.locality = item.locality
                            detail.municipality = item.municipality
                            detail.state = item.state
                            detail.function_name = item.function_name
                            detail.subfunction_name = item.subfunction_name
                            detail.program_name = item.program_name
                            detail.action_name = item.action_name
                            detail.plan_name = item.plan_name
                            detail.committed_amount = item.committed
                            detail.liquidated_amount = item.liquidated
                            detail.paid_amount = item.paid
                            detail.source = SOURCE
                            detail.source_url = PORTAL_AMENDMENTS_OPEN_DATA_URL
                            detail.collected_at = collected_at
                            detail.source_record_id = source_record.id

                    run = session.get(ImportRun, run_id)
                    run.status = "success"
                    run.finished_at = now()
                    run.received = source_metadata["amendments_in_file"]
                    run.inserted = inserted
                    run.updated = updated
                    run.unchanged = max(matched - inserted - updated, 0)
                    run.pages = 1
                return {
                    "run_id": str(run_id),
                    "status": "success",
                    "year": year,
                    "amendments": source_metadata["amendments_in_file"],
                    "matched_parliamentarians": matched,
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


if __name__ == "__main__":
    from app.core.config import get_settings

    settings = get_settings()
    today = local_today()
    print(
        json.dumps(
            import_portal_amendments_open_data(
                get_engine(), year=settings.portal_amendments_year or today.year
            ),
            ensure_ascii=False,
        )
    )
