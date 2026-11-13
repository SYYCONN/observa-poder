"""Importa o resumo da equipe em exercício dos gabinetes da Câmara."""

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.core.dates import local_today
from app.db.session import get_engine
from app.integrations.camara.staff import (
    CAMARA_STAFF_URL,
    enrich_staff_member,
    parse_staff_count,
    parse_staff_lotacoes,
    parse_staff_members,
    parse_staff_remuneration,
    staff_remuneration_url,
    staff_list_url,
)
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.financas.models import ParliamentaryStaffMember, ParliamentaryStaffSummary
from app.modules.parlamentares.models import Parliamentarian
from app.modules.proposicoes.linking import normalize_name

JOB = "camara.parliamentary_staff"
SOURCE = "camara"
LOCK_KEY = 2810302605
NORMALIZER_VERSION = "staff-members-v2"


def now():
    return datetime.now(timezone.utc)


def _match_lotacao(name: str, lotacoes: list[str]) -> str | None:
    """Associa gabinete somente por nome normalizado exato e único."""

    normalized = normalize_name(name)
    exact = [
        lotacao
        for lotacao in lotacoes
        if normalize_name(lotacao.removeprefix("Gabinete ")) == normalized
    ]
    return exact[0] if len(exact) == 1 else None


def import_camara_staff(engine, year: int, month: int, client=None):
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
                raise RuntimeError("Já existe uma importação de equipe em execução.")
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
                category_url = staff_list_url("")
                response = client.get(category_url)
                response.raise_for_status()
                lotacoes = parse_staff_lotacoes(response.text)
                if not lotacoes:
                    raise RuntimeError("A fonte não publicou a lista de gabinetes.")

                seen = now()
                payload_metadata = {
                    "year": year,
                    "month": month,
                    "lotacoes": len(lotacoes),
                    "category": "Secretário Parlamentar",
                    "status": "Em exercício",
                }
                digest = hashlib.sha256(
                    json.dumps(payload_metadata, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest()
                with Session(engine) as session, session.begin():
                    source_record = session.scalar(
                        select(SourceRecord).where(
                            SourceRecord.source == SOURCE,
                            SourceRecord.entity == "parliamentary_staff",
                            SourceRecord.external_id == f"{year}-{month:02d}",
                            SourceRecord.payload_hash == digest,
                            SourceRecord.normalizer_version == NORMALIZER_VERSION,
                        )
                    )
                    if source_record is None:
                        source_record = SourceRecord(
                            source=SOURCE,
                            entity="parliamentary_staff",
                            external_id=f"{year}-{month:02d}",
                            source_url=category_url,
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
                            select(ParliamentaryStaffSummary).where(
                                ParliamentaryStaffSummary.source == SOURCE,
                                ParliamentaryStaffSummary.year == year,
                                ParliamentaryStaffSummary.month == month,
                            )
                        )
                    }
                    inserted = updated = skipped = 0
                    members_inserted = 0
                    for person_name, person_id in people:
                        lotacao = _match_lotacao(person_name, lotacoes)
                        if lotacao is None:
                            skipped += 1
                            continue
                        query_url = staff_list_url(lotacao)
                        staff_response = client.get(query_url)
                        staff_response.raise_for_status()
                        count = parse_staff_count(staff_response.text)
                        members = [
                            enrich_staff_member(staff_response.text, member)
                            for member in parse_staff_members(staff_response.text)
                        ]
                        if count is None or not members:
                            skipped += 1
                            continue
                        key = (person_id, year, month)
                        row = existing.get(key)
                        if row is None:
                            row = ParliamentaryStaffSummary(
                                parliamentarian_id=person_id,
                                source=SOURCE,
                                year=year,
                                month=month,
                                staff_count=count,
                            )
                            session.add(row)
                            existing[key] = row
                            inserted += 1
                        else:
                            updated += 1
                        row.staff_count = count
                        row.source_query_url = query_url
                        row.source_url = category_url
                        row.collected_at = seen
                        row.source_record_id = source_record.id

                        # A competência representa uma fotografia do gabinete. Removemos
                        # os detalhes anteriores para não manter assessores que já saíram.
                        session.execute(
                            delete(ParliamentaryStaffMember).where(
                                ParliamentaryStaffMember.parliamentarian_id == person_id,
                                ParliamentaryStaffMember.source == SOURCE,
                                ParliamentaryStaffMember.year == year,
                                ParliamentaryStaffMember.month == month,
                            )
                        )
                        for member in members:
                            remuneration = {
                                "gross_amount": None,
                                "net_amount": None,
                                "allowances_amount": None,
                                "payroll_type": None,
                                "exercise_date": None,
                            }
                            remuneration_url = member.get("source_remuneration_url")
                            if remuneration_url:
                                try:
                                    remuneration_response = client.get(
                                        staff_remuneration_url(remuneration_url, year, month)
                                    )
                                    remuneration_response.raise_for_status()
                                    remuneration = parse_staff_remuneration(remuneration_response.text)
                                except httpx.HTTPError:
                                    # O cadastro do assessor continua útil mesmo quando a
                                    # página mensal de remuneração estiver indisponível.
                                    pass
                            session.add(
                                ParliamentaryStaffMember(
                                    external_id=member["external_id"],
                                    parliamentarian_id=person_id,
                                    source=SOURCE,
                                    year=year,
                                    month=month,
                                    name=member["name"] or "Nome não informado",
                                    category=member.get("category"),
                                    area_of_work=member.get("area_of_work"),
                                    job_title=member.get("job_title"),
                                    level=member.get("level"),
                                    gross_amount=remuneration.get("gross_amount"),
                                    net_amount=remuneration.get("net_amount"),
                                    allowances_amount=remuneration.get("allowances_amount"),
                                    source_query_url=query_url,
                                    source_remuneration_url=remuneration_url,
                                    payroll_type=remuneration.get("payroll_type"),
                                    exercise_date=remuneration.get("exercise_date"),
                                    source_url=category_url,
                                    collected_at=seen,
                                    source_record_id=source_record.id,
                                )
                            )
                            members_inserted += 1

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
                    "month": month,
                    "received": len(people),
                    "inserted": inserted,
                    "updated": updated,
                    "skipped": skipped,
                    "staff_members": members_inserted,
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
    today = local_today()
    print(
        json.dumps(
            import_camara_staff(get_engine(), today.year, today.month), ensure_ascii=False
        )
    )
