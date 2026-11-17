"""Exportação e recuperação explícita de registros públicos entre instalações."""

import argparse
import gzip
import hashlib
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Numeric, Uuid, select, text
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.integrations.camara.schemas import DeputyStatus
from app.jobs.import_camara_deputy_profiles import exercise_period
from app.jobs.import_senado_legislation import parse_date
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.financas.models import (
    ParliamentaryRemuneration, ParliamentaryStaffMember, ParliamentaryStaffSummary,
)
from app.modules.parlamentares.models import Mandate, Parliamentarian
from app.modules.proposicoes.models import Authorship, ProceedingsEvent, Proposition
from app.modules.votacoes.models import Vote, Voting, VotingProposition

MAX_BYTES = 64 * 1024**2
LOCKS = (2810202602, 2810202604, 2810202605, 2810202606, 2810202612, 2810302601, 2810302605)
SPECS = (
    (Proposition, ("source", "external_id")),
    (Voting, ("source", "external_id")),
    (Authorship, ("proposition_id", "source", "author_key")),
    (ProceedingsEvent, ("proposition_id", "source", "external_key")),
    (VotingProposition, ("voting_id", "proposition_id", "relation_type")),
    (Vote, ("voting_id", "parliamentarian_id")),
    (ParliamentaryStaffSummary, ("parliamentarian_id", "source", "year", "month")),
    (ParliamentaryStaffMember, ("parliamentarian_id", "source", "external_id", "year", "month")),
    (ParliamentaryRemuneration, ("parliamentarian_id", "source", "year", "month", "payroll_type")),
    (Mandate, ("parliamentarian_id", "source", "legislature_external_id")),
)


def serialize(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def export_snapshot(engine):
    with engine.connect() as connection, connection.begin():
        connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        with Session(bind=connection) as session:
            people = session.scalars(select(Parliamentarian)).all()
            person_ids = {(p.source, p.external_id): str(p.id) for p in people}
            records = {str(r.id): r for r in session.scalars(select(SourceRecord))}
            tables = {}
            for model, _ in SPECS:
                query = select(model)
                if model is Voting:
                    linked = select(VotingProposition.voting_id)
                    query = query.where((Voting.source == "senado") | Voting.id.in_(linked))
                elif model is Vote:
                    query = query.where(Vote.source == "senado", Vote.position != "registrado")
                elif model in (ParliamentaryStaffMember, ParliamentaryStaffSummary):
                    query = query.where(model.year == 2026, model.month == 10)
                elif model is Mandate:
                    continue
                tables[model.__tablename__] = [serialize(row) for row in session.scalars(query)]

            # As chaves do Senado são reconstruídas somente com a identidade oficial explícita.
            propositions = {str(p["id"]): p for p in tables["propositions"]}
            for prop in propositions.values():
                if prop["source"] == "senado":
                    origin = records[str(prop["source_record_id"])]
                    payload = origin.payload
                    document = payload.get("documento", {})
                    prop["full_text_url"] = document.get("url") or None
                    prop["status_description"] = payload.get("situacaoAtual") or None
                    value = payload.get("dataSituacaoAtual")
                    if value:
                        prop["status_at"] = parse_date(value)
                    prop["official_detail_collected_at"] = prop["collected_at"]
                    keywords = document.get("indexacao")
                    if isinstance(keywords, str):
                        prop["keywords"] = [
                            value.strip() for value in re.split(r"[,;]", keywords) if value.strip()
                        ]
            for author in tables["authorships"]:
                if author["source"] != "senado":
                    continue
                prop = propositions[str(author["proposition_id"])]
                origin = records[str(prop["source_record_id"])]
                payload = origin.payload
                authors = payload.get("documento", {}).get("autoria") or []
                initiatives = payload.get("autoriaIniciativa") or []
                if isinstance(authors, dict):
                    authors = [authors]
                if isinstance(initiatives, dict):
                    initiatives = [initiatives]
                candidates = [
                    (index, item) for index, item in enumerate(authors + initiatives, 1)
                    if isinstance(item, dict)
                    and item.get("autor") == author["author_name"]
                    and item.get("siglaTipo") == "SENADOR"
                    and item.get("casaEnte") == "SF"
                    and str(item.get("codigoParlamentar", "")).isascii()
                    and str(item.get("codigoParlamentar", "")).isdigit()
                ]
                author["parliamentarian_id"] = None
                identifiers = {str(item["codigoParlamentar"]) for _, item in candidates}
                if len(identifiers) == 1:
                    index, item = candidates[0]
                    identifier = str(item["codigoParlamentar"])
                    author["author_key"] = f"senador:{identifier}:{index}"
                    author["parliamentarian_id"] = person_ids.get(("senado", identifier))
                    author["source_record_id"] = prop["source_record_id"]

            histories = {}
            for record in records.values():
                if record.entity == "historico_deputado" and "/historico" in record.source_url:
                    previous = histories.get(record.external_id)
                    if previous is None or record.last_seen_at > previous.last_seen_at:
                        histories[record.external_id] = record
            people_by_id = {p.id: p for p in people}
            mandates = []
            for mandate in session.scalars(select(Mandate).where(Mandate.source == "camara")):
                person = people_by_id[mandate.parliamentarian_id]
                origin = histories.get(person.external_id)
                if origin is None:
                    continue
                events = [
                    DeputyStatus.model_validate(
                        {"id": int(person.external_id), **item}, strict=False
                    )
                    for item in origin.payload["historico"]
                ]
                start, end = exercise_period(events, mandate.legislature_external_id)
                if start is None and end is None:
                    continue
                row = serialize(mandate)
                row.update(started_on=start, ended_on=end, source_record_id=origin.id,
                           source_url=origin.source_url, collected_at=origin.last_seen_at)
                mandates.append(row)
            tables["mandates"] = mandates
            used_sources = {
                str(row["source_record_id"]) for rows in tables.values() for row in rows
            }
            sources = []
            for identifier in sorted(used_sources):
                origin = records[identifier]
                metadata = {
                    "original_payload_hash": origin.payload_hash,
                    "original_normalizer_version": origin.normalizer_version,
                    "original_source_record_id": identifier,
                }
                sources.append({
                    "id": identifier, "source": origin.source, "entity": origin.entity,
                    "external_id": origin.external_id, "source_url": origin.source_url,
                    "first_seen_at": origin.first_seen_at, "last_seen_at": origin.last_seen_at,
                    "payload": metadata,
                    "payload_hash": hashlib.sha256(
                        json.dumps(metadata, sort_keys=True).encode()
                    ).hexdigest(),
                    "normalizer_version": "public-recovery-v1",
                })
            return {
                "format": 1, "created_at": datetime.now(timezone.utc).isoformat(),
                "people": {str(p.id): [p.source, p.external_id] for p in people},
                "sources": sources, "tables": tables,
            }


def typed_row(model, row):
    columns = model.__table__.columns
    if set(row) - set(columns.keys()):
        raise ValueError("O pacote contém campos desconhecidos.")
    result = dict(row)
    for name, value in result.items():
        if value is None:
            continue
        column_type = columns[name].type
        if isinstance(column_type, DateTime):
            result[name] = datetime.fromisoformat(value)
        elif isinstance(column_type, Date):
            result[name] = date.fromisoformat(value)
        elif isinstance(column_type, Numeric):
            result[name] = Decimal(value)
        elif isinstance(column_type, Uuid):
            result[name] = UUID(value)
    return result


def recover_snapshot(engine, bundle, apply=False):
    if bundle.get("format") != 1 or set(bundle["tables"]) != {m.__tablename__ for m, _ in SPECS}:
        raise ValueError("Formato do pacote de recuperação inválido.")
    mappings = {}
    counts = {}
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with Session(bind=connection) as session:
                for key in LOCKS:
                    if not session.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": key}):
                        raise RuntimeError("Existe uma coleta concorrente. Repita após sua conclusão.")
                run = ImportRun(job="portal.public_snapshot_recovery", status="running",
                                started_at=datetime.now(timezone.utc))
                session.add(run)
                session.flush()
                people = {
                    (p.source, p.external_id): p.id for p in session.scalars(select(Parliamentarian))
                }
                mappings["parliamentarians"] = {}
                for identifier, key in bundle["people"].items():
                    if tuple(key) not in people:
                        raise ValueError("Um parlamentar do pacote ainda não está cadastrado no destino.")
                    mappings["parliamentarians"][identifier] = people[tuple(key)]
                mappings["source_records"] = {}
                for row in bundle["sources"]:
                    values = typed_row(SourceRecord, row)
                    identifier = str(values.pop("id"))
                    existing = session.scalar(select(SourceRecord).where(*(
                        getattr(SourceRecord, key) == values[key]
                        for key in ("source", "entity", "external_id", "payload_hash", "normalizer_version")
                    )))
                    if existing is None:
                        existing = SourceRecord(**values, last_run_id=run.id)
                        session.add(existing)
                        session.flush()
                    mappings["source_records"][identifier] = existing.id
                for model, keys in SPECS:
                    table = model.__table__
                    mappings[table.name] = {}
                    inserted = updated = 0
                    for row in bundle["tables"][table.name]:
                        values = typed_row(model, row)
                        original_id = str(values.pop("id", ""))
                        for column in table.columns:
                            value = values.get(column.name)
                            if value is not None and column.foreign_keys:
                                foreign = next(iter(column.foreign_keys)).column.table.name
                                values[column.name] = mappings[foreign][str(value)]
                        conditions = [table.c[key] == values[key] for key in keys]
                        existing = session.execute(select(table).where(*conditions)).mappings().first()
                        if existing is None:
                            if "id" in table.c:
                                values["id"] = uuid4()
                            session.execute(table.insert().values(**values))
                            inserted += 1
                            target_id = values.get("id")
                        else:
                            target_id = existing.get("id")
                            if model is Proposition:
                                fields = (
                                    "full_text_url", "status_description", "status_at", "keywords",
                                    "official_detail_collected_at",
                                )
                                updates = {
                                    key: values[key] for key in fields
                                    if not existing[key] and values.get(key)
                                }
                                if updates:
                                    session.execute(table.update().where(*conditions).values(**updates))
                                    updated += 1
                            if model is Mandate:
                                # A origem individual tem precedência sobre a coleção em lote.
                                origin = session.get(SourceRecord, existing["source_record_id"])
                                if "/historico" not in origin.source_url:
                                    updates = {key: values[key] for key in (
                                        "started_on", "ended_on", "source_url",
                                        "source_record_id", "collected_at",
                                    )}
                                    session.execute(table.update().where(*conditions).values(**updates))
                                    updated += 1
                        if original_id:
                            mappings[table.name][original_id] = target_id
                    counts[table.name] = {"inserted": inserted, "updated": updated}
                run.status = "success"
                run.finished_at = datetime.now(timezone.utc)
                run.inserted = sum(c["inserted"] for c in counts.values())
                run.updated = sum(c["updated"] for c in counts.values())
                session.flush()
            if apply:
                transaction.commit()
            else:
                transaction.rollback()
        except Exception:
            transaction.rollback()
            raise
    return {"status": "success", "applied": apply, "counts": counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("path")
    restore = commands.add_parser("import")
    restore.add_argument("path")
    restore.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    path = Path(args.path)
    if args.command == "export":
        bundle = export_snapshot(get_engine())
        raw = json.dumps(bundle, default=str, ensure_ascii=False).encode()
        if len(raw) > MAX_BYTES:
            raise ValueError("O pacote excede o limite de recuperação.")
        path.write_bytes(gzip.compress(raw))
        result = {"tables": {name: len(rows) for name, rows in bundle["tables"].items()}}
    else:
        with gzip.open(path, "rb") as source:
            raw = source.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("O pacote excede o limite de recuperação.")
        result = recover_snapshot(get_engine(), json.loads(raw), apply=args.apply)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
