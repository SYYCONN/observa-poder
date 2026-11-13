"""Importa o resumo anual de emendas de autoria dos deputados."""

import hashlib
import json
import time
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import httpx
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.dates import local_today
from app.db.session import get_engine
from app.core.config import get_settings
from app.integrations.portal_transparencia.amendments import (
    PORTAL_AMENDMENTS_API_URL,
    PORTAL_AMENDMENTS_SOURCE_URL,
    amendments_api_params,
    amendments_query_url,
    parse_amendments,
)
from app.integrations.portal_transparencia.open_data import normalize_author_name
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.financas.models import ParliamentaryAmendmentSummary
from app.modules.parlamentares.models import Parliamentarian

JOB = "portal.parliamentary_amendments"
SOURCE = "portal_transparencia"
LOCK_KEY = 2810302607
NORMALIZER_VERSION = "portal-amendments-summary-v1"


def now():
    return datetime.now(timezone.utc)


def _complete_sum(values) -> Decimal | None:
    values = list(values)
    if not values or any(value is None for value in values):
        return None
    return sum(values, Decimal("0"))


def import_portal_amendments(
    engine,
    year: int,
    api_token: str,
    client=None,
    request_interval_seconds: float = 0.25,
):
    if not api_token:
        raise RuntimeError("A chave da API do Portal da Transparência não foi configurada.")
    owns_client = client is None
    client = client or httpx.Client(
        timeout=httpx.Timeout(30, connect=10),
        follow_redirects=False,
        headers={"Accept": "application/json", "chave-api-dados": api_token},
    )
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

                with Session(engine) as session:
                    people = list(
                        session.execute(
                            select(Parliamentarian.name, Parliamentarian.id).where(
                                Parliamentarian.source == "camara"
                            )
                        )
                    )
                name_counts: dict[str, int] = {}
                for name, _ in people:
                    key = normalize_author_name(name)
                    name_counts[key] = name_counts.get(key, 0) + 1
                seen = now()
                payload_metadata = {"year": year, "parliamentarians": len(people)}
                digest = hashlib.sha256(
                    json.dumps(payload_metadata, sort_keys=True).encode("utf-8")
                ).hexdigest()
                with Session(engine) as session, session.begin():
                    source_record = session.scalar(
                        select(SourceRecord).where(
                            SourceRecord.source == SOURCE,
                            SourceRecord.entity == "parliamentary_amendments",
                            SourceRecord.external_id == str(year),
                            SourceRecord.payload_hash == digest,
                            SourceRecord.normalizer_version == NORMALIZER_VERSION,
                        )
                    )
                    if source_record is None:
                        source_record = SourceRecord(
                            source=SOURCE,
                            entity="parliamentary_amendments",
                            external_id=str(year),
                            source_url=PORTAL_AMENDMENTS_SOURCE_URL,
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
                        (row.parliamentarian_id, row.year): row
                        for row in session.scalars(
                            select(ParliamentaryAmendmentSummary).where(
                                ParliamentaryAmendmentSummary.source == SOURCE,
                                ParliamentaryAmendmentSummary.year == year,
                            )
                        )
                    }
                    inserted = updated = skipped = 0
                    last_request_at = 0.0
                    for name, person_id in people:
                        normalized_name = normalize_author_name(name)
                        if not normalized_name or name_counts[normalized_name] != 1:
                            skipped += 1
                            continue
                        records = []
                        for page in range(1, 101):
                            elapsed = time.monotonic() - last_request_at
                            if elapsed < request_interval_seconds:
                                time.sleep(request_interval_seconds - elapsed)
                            response = client.get(
                                PORTAL_AMENDMENTS_API_URL,
                                params=amendments_api_params(name, year, page),
                            )
                            last_request_at = time.monotonic()
                            response.raise_for_status()
                            try:
                                payload = response.json()
                            except ValueError as exc:
                                detail = response.text.strip().replace("\n", " ")[:300]
                                raise RuntimeError(
                                    "A API de emendas não retornou JSON "
                                    f"(status {response.status_code}): {detail}"
                                ) from exc
                            if not isinstance(payload, list):
                                raise RuntimeError(
                                    "A API de emendas retornou um formato inesperado "
                                    f"(status {response.status_code})."
                                )
                            page_records = [
                                record
                                for record in parse_amendments(payload)
                                if normalize_author_name(record.get("author")) == normalized_name
                            ]
                            records.extend(page_records)
                            if len(page_records) < 15:
                                break
                        unique = {record["code"]: record for record in records}
                        if not unique:
                            skipped += 1
                            continue
                        row = existing.get((person_id, year))
                        if row is None:
                            row = ParliamentaryAmendmentSummary(
                                parliamentarian_id=person_id,
                                source=SOURCE,
                                year=year,
                                amendment_count=len(unique),
                            )
                            session.add(row)
                            existing[(person_id, year)] = row
                            inserted += 1
                        else:
                            updated += 1
                        row.amendment_count = len(unique)
                        row.committed_amount = _complete_sum(
                            item["committed"] for item in unique.values()
                        )
                        row.liquidated_amount = _complete_sum(
                            item["liquidated"] for item in unique.values()
                        )
                        row.paid_amount = _complete_sum(
                            item["paid"] for item in unique.values()
                        )
                        row.source_query_url = amendments_query_url(name, year)
                        row.source_url = PORTAL_AMENDMENTS_SOURCE_URL
                        row.collected_at = seen
                        row.source_record_id = source_record.id

                    run = session.get(ImportRun, run_id)
                    run.status = "success"
                    run.finished_at = now()
                    run.received = len(people)
                    run.inserted = inserted
                    run.updated = updated
                    run.unchanged = max(len(people) - skipped - inserted - updated, 0)
                    run.pages = 1
                return {
                    "run_id": str(run_id),
                    "status": "success",
                    "year": year,
                    "received": len(people),
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
    settings = get_settings()
    token = settings.portal_transparencia_api_token
    if token is None:
        raise SystemExit("Configure PORTAL_TRANSPARENCIA_API_TOKEN antes da coleta.")
    today = local_today()
    print(
        json.dumps(
            import_portal_amendments(
                get_engine(),
                year=settings.portal_amendments_year or today.year,
                api_token=token.get_secret_value(),
                request_interval_seconds=settings.portal_amendments_request_interval_seconds,
            ),
            ensure_ascii=False,
        )
    )
