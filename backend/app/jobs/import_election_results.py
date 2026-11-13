"""Importa votos nominais das eleições gerais a partir do arquivo oficial do TSE.

O arquivo do TSE é grande e fica apenas em um arquivo temporário durante a coleta.
O banco guarda o agregado por parlamentar, cargo, UF e eleição; não guarda o CSV bruto.
"""

import argparse
import csv
import hashlib
import io
import json
import re
import tempfile
import unicodedata
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.parlamentares.models import ElectionResult, Mandate, Parliamentarian

JOB = "tse.election_results"
LOCK_KEY = 2810202607
DEFAULT_YEAR = 2022
TSE_ARCHIVE_TEMPLATE = (
    "https://cdn.tse.jus.br/estatistica/sead/odsele/"
    "votacao_candidato_munzona/votacao_candidato_munzona_{year}.zip"
)
TSE_DATASET_URL = "https://dadosabertos.tse.jus.br/dataset/resultados-{year}"

# Nas eleições gerais, 5 é senador e 6 é deputado federal.
OFFICES = {
    "5": ("senado", "Senador"),
    "6": ("camara", "Deputado federal"),
}


class ImportBusy(Exception):
    pass


class ImportFailed(Exception):
    pass


def now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    folded = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in folded if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", without_accents.casefold()).strip()


def integer(value: str | None) -> int:
    if not value or value in {"#NULO", "#NE", "-"}:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def current_people(session: Session) -> dict[tuple[str, str, str], list[Parliamentarian]]:
    rows = session.execute(
        select(Parliamentarian, Mandate)
        .join(Mandate, Mandate.parliamentarian_id == Parliamentarian.id)
        .where(Parliamentarian.source.in_(tuple(source for source, _ in OFFICES.values())))
    ).all()
    latest: dict[UUID, tuple[Parliamentarian, Mandate]] = {}
    for person, mandate in rows:
        previous = latest.get(person.id)
        if previous is None or (
            mandate.legislature_external_id > previous[1].legislature_external_id
        ):
            latest[person.id] = (person, mandate)

    matches: dict[tuple[str, str, str], list[Parliamentarian]] = defaultdict(list)
    for person, mandate in latest.values():
        aliases = {person.name}
        if person.profile_source_record_id:
            profile_record = session.get(SourceRecord, person.profile_source_record_id)
            civil_name = (profile_record.payload or {}).get("nomeCivil") if profile_record else None
            if isinstance(civil_name, str) and civil_name.strip():
                aliases.add(civil_name)
        for alias in aliases:
            key = (person.source, mandate.state, normalize_name(alias))
            if key[2] and person not in matches[key]:
                matches[key].append(person)
    return matches


def aggregate_archive(
    archive: zipfile.ZipFile,
    states: set[str],
) -> tuple[dict[tuple[str, str, str, str, str, str, str, str], tuple[int, int]], int]:
    aggregates: dict[
        tuple[str, str, str, str, str, str, str, str], list[int]
    ] = defaultdict(lambda: [0, 0])
    files = 0
    for member in archive.namelist():
        match = re.search(r"_([A-Z]{2})\.csv$", member)
        if not match or match.group(1) not in states:
            continue
        files += 1
        with archive.open(member) as raw:
            text_stream = io.TextIOWrapper(raw, encoding="latin1", newline="")
            reader = csv.DictReader(text_stream, delimiter=";")
            required = {"NR_TURNO", "CD_CARGO", "SG_UF", "SQ_CANDIDATO", "NM_CANDIDATO"}
            if not required.issubset(reader.fieldnames or set()):
                raise ValueError(f"Arquivo do TSE sem colunas esperadas: {member}")
            for row in reader:
                office = OFFICES.get(row.get("CD_CARGO", ""))
                if office is None or row.get("NR_TURNO") != "1":
                    continue
                source, _ = office
                state = (row.get("SG_UF") or "").upper()
                key = (
                    source,
                    state,
                    row.get("SQ_CANDIDATO") or "",
                    row.get("NR_CANDIDATO") or "",
                    row.get("NM_CANDIDATO") or "",
                    row.get("NM_URNA_CANDIDATO") or "",
                    row.get("SG_PARTIDO") or "",
                    row.get("DS_SIT_TOT_TURNO") or "",
                )
                aggregates[key][0] += integer(row.get("QT_VOTOS_NOMINAIS"))
                aggregates[key][1] += integer(row.get("QT_VOTOS_NOMINAIS_VALIDOS"))
    return {key: (values[0], values[1]) for key, values in aggregates.items()}, files


def source_record(
    session: Session,
    run_id: UUID,
    external_id: str,
    url: str,
    payload: dict,
    collected_at: datetime,
) -> SourceRecord:
    payload_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    record = session.scalar(
        select(SourceRecord).where(
            SourceRecord.source == "tse",
            SourceRecord.entity == "resultado_eleitoral",
            SourceRecord.external_id == external_id,
            SourceRecord.payload_hash == payload_hash,
            SourceRecord.normalizer_version == "tse-results-v1",
        )
    )
    if record is None:
        record = SourceRecord(
            source="tse",
            entity="resultado_eleitoral",
            external_id=external_id,
            source_url=url,
            payload_hash=payload_hash,
            normalizer_version="tse-results-v1",
            payload=payload,
            first_seen_at=collected_at,
            last_seen_at=collected_at,
            last_run_id=run_id,
        )
        session.add(record)
        session.flush()
    else:
        record.last_seen_at = collected_at
        record.last_run_id = run_id
    return record


def download_archive(client: httpx.Client, year: int, destination: Path) -> None:
    url = TSE_ARCHIVE_TEMPLATE.format(year=year)
    with client.stream("GET", url) as response:
        response.raise_for_status()
        with destination.open("wb") as output:
            for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                output.write(chunk)


def import_election_results(
    engine,
    year: int = DEFAULT_YEAR,
    archive_path: str | None = None,
    client: httpx.Client | None = None,
) -> dict[str, int | str]:
    owns_client = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(180, connect=15), follow_redirects=True)
    run_id = uuid4()
    collected_at = now()
    temporary_path: Path | None = None
    try:
        with engine.connect() as lock:
            if not lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}):
                raise ImportBusy(
                    "Já existe uma importação de resultados eleitorais em execução."
                )
            lock.commit()
            try:
                with Session(engine) as session, session.begin():
                    session.execute(
                        update(ImportRun)
                        .where(ImportRun.job == JOB, ImportRun.status == "running")
                        .values(
                            status="interrupted",
                            finished_at=collected_at,
                            error_code="interrupted",
                        )
                    )
                    session.add(
                        ImportRun(id=run_id, job=JOB, status="running", started_at=collected_at)
                    )

                with Session(engine) as session:
                    matches = current_people(session)
                states = {state for _, state, _ in matches}

                if archive_path:
                    archive = Path(archive_path)
                else:
                    temporary = tempfile.NamedTemporaryFile(
                        prefix="tse-results-", suffix=".zip", delete=False
                    )
                    temporary_path = Path(temporary.name)
                    temporary.close()
                    download_archive(client, year, temporary_path)
                    archive = temporary_path

                with zipfile.ZipFile(archive) as zipped:
                    aggregates, files = aggregate_archive(zipped, states)

                inserted = updated = unchanged = matched = 0
                with Session(engine) as session, session.begin():
                    for key, (votes, valid_votes) in aggregates.items():
                        (
                            source,
                            state,
                            candidate_id,
                            candidate_number,
                            candidate_name,
                            ballot_name,
                            party,
                            status,
                        ) = key
                        names = {normalize_name(candidate_name), normalize_name(ballot_name)} - {""}
                        candidates = {
                            person.id: person
                            for name in names
                            for person in matches.get((source, state, name), [])
                        }
                        if len(candidates) != 1:
                            continue
                        person = next(iter(candidates.values()))
                        matched += 1
                        external_id = f"{year}:1:{source}:{state}:{candidate_id}"
                        payload = {
                            "year": year,
                            "round": 1,
                            "office": "Senador" if source == "senado" else "Deputado federal",
                            "state": state,
                            "candidate_id": candidate_id,
                            "candidate_number": candidate_number,
                            "candidate_name": candidate_name,
                            "ballot_name": ballot_name,
                            "party": party,
                            "votes": votes,
                            "valid_votes": valid_votes,
                            "status": status,
                        }
                        record = source_record(
                            session,
                            run_id,
                            external_id,
                            TSE_DATASET_URL.format(year=year),
                            payload,
                            collected_at,
                        )
                        result = session.scalar(
                            select(ElectionResult).where(
                                ElectionResult.parliamentarian_id == person.id,
                                ElectionResult.source == "tse",
                                ElectionResult.election_year == year,
                                ElectionResult.office == payload["office"],
                            )
                        )
                        if result is None:
                            result = ElectionResult(
                                parliamentarian_id=person.id,
                                source="tse",
                                election_year=year,
                                office=payload["office"],
                            )
                            session.add(result)
                            inserted += 1
                        elif (
                            result.votes,
                            result.valid_votes,
                            result.election_status,
                            result.party,
                        ) == (votes, valid_votes, status, party):
                            unchanged += 1
                        else:
                            updated += 1
                        result.election_round = 1
                        result.state = state
                        result.candidate_number = candidate_number
                        result.candidate_name = candidate_name
                        result.party = party
                        result.votes = votes
                        result.valid_votes = valid_votes
                        result.election_status = status
                        result.source_url = TSE_DATASET_URL.format(year=year)
                        result.collected_at = collected_at
                        result.source_record_id = record.id

                    run = session.get(ImportRun, run_id)
                    run.status = "success"
                    run.finished_at = now()
                    run.pages = files
                    run.received = len(aggregates)
                    run.inserted = inserted
                    run.updated = updated
                    run.unchanged = unchanged
                return {
                    "run_id": str(run_id),
                    "status": "success",
                    "files": files,
                    "candidates": len(aggregates),
                    "matched": matched,
                    "inserted": inserted,
                    "updated": updated,
                    "unchanged": unchanged,
                }
            except Exception as exc:
                with Session(engine) as session, session.begin():
                    run = session.get(ImportRun, run_id)
                    if run:
                        run.status = "failed"
                        run.finished_at = now()
                        run.error_code = "processing_error"
                        run.error_message = type(exc).__name__
                raise ImportFailed(str(exc)) from exc
            finally:
                lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY})
                lock.commit()
    finally:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)
        if owns_client:
            client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--archive", help="Arquivo ZIP local já baixado, opcional")
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                import_election_results(get_engine(), args.year, args.archive), ensure_ascii=False
            )
        )
    except (ImportBusy, ImportFailed) as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
