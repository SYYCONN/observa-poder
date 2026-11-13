"""Importa votos nominais anuais da Câmara a partir dos arquivos oficiais."""

import csv
import hashlib
import tempfile
from random import random
import time
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx

from app.integrations.download import bounded_chunks
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.core.dates import local_today
from app.integrations.camara.schemas import BASE_URL, STATES
from app.integrations.legislation import legislative_datetime
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.parlamentares.models import Mandate, Parliamentarian
from app.modules.votacoes.models import Vote, Voting

SOURCE = "camara"
JOB = "camara.annual_votes"
LOCK_KEY = 2810202605
NORMALIZER_VERSION = "camara-votes-v1"
VOTINGS_URL = "https://dadosabertos.camara.leg.br/arquivos/votacoes/csv/votacoes-{year}.csv"
VOTES_URL = "https://dadosabertos.camara.leg.br/arquivos/votacoesVotos/csv/votacoesVotos-{year}.csv"


def now() -> datetime:
    return datetime.now(timezone.utc)


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return legislative_datetime(value)
    except ValueError:
        return None


def parse_bool(value: str | None) -> bool | None:
    if value == "1":
        return True
    if value == "0":
        return False
    return None


def download(client: httpx.Client, url: str) -> Path:
    temporary = tempfile.NamedTemporaryFile(prefix="camara-votes-", suffix=".csv", delete=False)
    path = Path(temporary.name)
    temporary.close()
    deadline = time.monotonic() + 300
    try:
        for attempt in range(3):
            try:
                with path.open("wb") as destination, client.stream(
                    "GET", url, follow_redirects=False
                ) as response:
                    for chunk in bounded_chunks(response, 160 * 1024**2, deadline):
                        destination.write(chunk)
                if path.stat().st_size == 0:
                    raise httpx.ReadError("Arquivo anual vazio.")
                return path
            except httpx.HTTPStatusError as exc:
                if (exc.response.status_code != 429 and exc.response.status_code < 500) or attempt == 2:
                    raise
            except httpx.TransportError:
                if attempt == 2:
                    raise
            delay = 2**attempt + random()
            if time.monotonic() + delay >= deadline:
                raise ValueError("Prazo de download excedido.")
            time.sleep(delay)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    raise AssertionError("unreachable")


def rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        yield from csv.DictReader(file, delimiter=";")


def source_file(
    session: Session, run_id, year: int, entity: str, url: str, seen: datetime
) -> SourceRecord:
    digest = hashlib.sha256(f"{url}|{year}|{NORMALIZER_VERSION}".encode()).hexdigest()
    record = session.scalar(
        select(SourceRecord).where(
            SourceRecord.source == SOURCE,
            SourceRecord.entity == entity,
            SourceRecord.external_id == str(year),
            SourceRecord.payload_hash == digest,
            SourceRecord.normalizer_version == NORMALIZER_VERSION,
        )
    )
    if record is None:
        record = SourceRecord(
            source=SOURCE,
            entity=entity,
            external_id=str(year),
            source_url=url,
            payload_hash=digest,
            normalizer_version=NORMALIZER_VERSION,
            payload={"year": year, "format": "csv", "url": url},
            first_seen_at=seen,
            last_seen_at=seen,
            last_run_id=run_id,
        )
        session.add(record)
        session.flush()
    else:
        record.last_seen_at = seen
        record.last_run_id = run_id
    return record


def import_camara_votes(engine, year: int | None = None, client=None):
    """Importa o ano indicado sem inferir votos de parlamentares ausentes."""
    year = year or local_today().year
    owns_client = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(300, connect=20), follow_redirects=True)
    run_id = uuid4()
    started = now()
    votings_path = votes_path = None
    try:
        with engine.connect() as lock:
            if not lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}):
                raise RuntimeError("Já existe uma importação de votos da Câmara em execução.")
            lock.commit()
            try:
                with Session(engine) as session, session.begin():
                    session.add(ImportRun(id=run_id, job=JOB, status="running", started_at=started))

                votings_url = VOTINGS_URL.format(year=year)
                votes_url = VOTES_URL.format(year=year)
                votings_path = download(client, votings_url)
                votes_path = download(client, votes_url)
                seen = now()
                with Session(engine) as session, session.begin():
                    votings_record = source_file(
                        session, run_id, year, "votings_file", votings_url, seen
                    )
                    votes_record = source_file(session, run_id, year, "votes_file", votes_url, seen)
                    people = dict(
                        session.execute(
                            select(Parliamentarian.external_id, Parliamentarian.id).where(
                                Parliamentarian.source == SOURCE
                            )
                        ).all()
                    )
                    # O arquivo anual também identifica suplentes e ex-deputados que
                    # não aparecem na lista atual. Criamos somente perfis sustentados
                    # pelos identificadores e campos oficiais presentes no próprio CSV.
                    historical_identities: dict[str, dict[str, str]] = {}
                    for item in rows(votes_path):
                        external_id = (item.get("deputado_id") or "").strip()
                        if not external_id or external_id in people:
                            continue
                        expected_uri = f"{BASE_URL}/deputados/{external_id}"
                        state = (item.get("deputado_siglaUf") or "").strip()
                        legislature = (item.get("deputado_idLegislatura") or "").strip()
                        name = (item.get("deputado_nome") or "").strip()
                        if (
                            item.get("deputado_uri") != expected_uri
                            or state not in STATES
                            or not legislature
                            or not name
                        ):
                            continue
                        previous = historical_identities.get(external_id)
                        if previous is None or (item.get("dataHoraVoto") or "") > (
                            previous.get("dataHoraVoto") or ""
                        ):
                            historical_identities[external_id] = item

                    people_inserted = 0
                    for external_id, item in historical_identities.items():
                        person = Parliamentarian(
                            source=SOURCE,
                            external_id=external_id,
                            name=(item.get("deputado_nome") or "").strip()[:250],
                            photo_url=(item.get("deputado_urlFoto") or "").strip()[:1000] or None,
                            is_current=False,
                            source_url=item["deputado_uri"],
                            source_record_id=votes_record.id,
                            collected_at=seen,
                        )
                        session.add(person)
                        session.flush()
                        mandate = Mandate(
                            parliamentarian_id=person.id,
                            source=SOURCE,
                            legislature_external_id=(
                                item.get("deputado_idLegislatura") or ""
                            ).strip()[:100],
                            state=(item.get("deputado_siglaUf") or "").strip(),
                            party=(item.get("deputado_siglaPartido") or "").strip()[:40] or None,
                            party_source_url=(item.get("deputado_uriPartido") or "").strip()[:1000]
                            or None,
                            source_url=item["deputado_uri"],
                            source_record_id=votes_record.id,
                            collected_at=seen,
                        )
                        session.add(mandate)
                        people[external_id] = person.id
                        people_inserted += 1
                    voting_rows = {
                        row.external_id: row
                        for row in session.scalars(select(Voting).where(Voting.source == SOURCE))
                    }
                    received = inserted = updated = skipped = 0
                    for item in rows(votings_path):
                        external_id = (item.get("id") or "").strip()
                        if not external_id:
                            skipped += 1
                            continue
                        row = voting_rows.get(external_id)
                        if row is None:
                            row = Voting(source=SOURCE, external_id=external_id, description="")
                            session.add(row)
                            voting_rows[external_id] = row
                            inserted += 1
                        else:
                            updated += 1
                        row.occurred_on = parse_date(item.get("data"))
                        row.registered_at = parse_datetime(item.get("dataHoraRegistro"))
                        row.description = item.get("descricao") or "Descrição não informada"
                        row.object_description = (
                            item.get("ultimaApresentacaoProposicao_descricao") or None
                        )
                        row.agency_url = item.get("uriOrgao") or None
                        row.approved = parse_bool(item.get("aprovacao"))
                        row.source_url = item.get("uri") or votings_url
                        row.collected_at = seen
                        row.source_record_id = votings_record.id
                        received += 1
                        if received % 2000 == 0:
                            session.flush()

                    vote_received = vote_inserted = vote_updated = vote_skipped = 0
                    existing_votes = {
                        (vote.voting_id, vote.parliamentarian_id): vote
                        for vote in session.scalars(
                            select(Vote)
                            .join(Voting, Voting.id == Vote.voting_id)
                            .where(Voting.source == SOURCE)
                        )
                    }
                    for item in rows(votes_path):
                        external_id = (item.get("idVotacao") or "").strip()
                        person_id = people.get((item.get("deputado_id") or "").strip())
                        voting = voting_rows.get(external_id)
                        position = (item.get("voto") or "").strip()
                        if not external_id or voting is None or person_id is None or not position:
                            vote_skipped += 1
                            continue
                        voting.mode = "nominal"
                        key = (voting.id, person_id)
                        vote = existing_votes.get(key)
                        if vote is None:
                            vote = Vote(
                                voting_id=voting.id, parliamentarian_id=person_id, position=position
                            )
                            session.add(vote)
                            existing_votes[key] = vote
                            vote_inserted += 1
                        else:
                            vote_updated += 1
                        vote.position = position
                        vote.registered_at = parse_datetime(item.get("dataHoraVoto"))
                        vote.party_at_vote = item.get("deputado_siglaPartido") or None
                        vote.state_at_vote = item.get("deputado_siglaUf") or None
                        vote.source = SOURCE
                        vote.source_url = item.get("uriVotacao") or votes_url
                        vote.collected_at = seen
                        vote.source_record_id = votes_record.id
                        vote_received += 1
                        if vote_received % 5000 == 0:
                            session.flush()

                    run = session.get(ImportRun, run_id)
                    run.status = "success"
                    run.finished_at = now()
                    run.received = received + vote_received
                    run.inserted = people_inserted + inserted + vote_inserted
                    run.updated = updated + vote_updated
                    run.unchanged = 0
                return {
                    "run_id": str(run_id),
                    "status": "success",
                    "year": year,
                    "votings": received,
                    "votes": vote_received,
                    "votings_inserted": inserted,
                    "votes_inserted": vote_inserted,
                    "parliamentarians_inserted": people_inserted,
                    "skipped": skipped + vote_skipped,
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
        for path in (votings_path, votes_path):
            if path:
                path.unlink(missing_ok=True)
        if owns_client:
            client.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=local_today().year)
    args = parser.parse_args()
    print(import_camara_votes(get_engine(), year=args.year))
