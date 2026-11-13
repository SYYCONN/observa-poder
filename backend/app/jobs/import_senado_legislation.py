"""Importa uma janela controlada de processos e votações nominais do Senado."""

import hashlib
import json
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.integrations.legislation import vote_position
from app.core.dates import BUSINESS_TIMEZONE, local_today
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.parlamentares.models import Parliamentarian
from app.modules.proposicoes.models import Authorship, ProceedingsEvent, Proposition
from app.modules.votacoes.models import Vote, Voting, VotingProposition

BASE = "https://legis.senado.leg.br/dadosabertos"
SOURCE = "senado"
JOB = "senado.recent_legislation"
LOCK_KEY = 2810202604
MAX_PROCESS_BYTES = 12_000_000
MAX_VOTING_BYTES = 4_000_000


def now():
    return datetime.now(timezone.utc)


def parse_date(value: str | None):
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BUSINESS_TIMEZONE)
    return parsed.astimezone(timezone.utc)


def source_record(
    session: Session,
    run_id: UUID,
    entity: str,
    external_id: str,
    url: str,
    payload: dict,
    seen: datetime,
):
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    row = session.scalar(
        select(SourceRecord).where(
            SourceRecord.source == SOURCE,
            SourceRecord.entity == entity,
            SourceRecord.external_id == external_id,
            SourceRecord.payload_hash == digest,
            SourceRecord.normalizer_version == "senado-legislacao-v1",
        )
    )
    if row:
        row.last_seen_at, row.last_run_id = seen, run_id
        return row
    row = SourceRecord(
        source=SOURCE,
        entity=entity,
        external_id=external_id,
        source_url=url,
        payload_hash=digest,
        normalizer_version="senado-legislacao-v1",
        payload=payload,
        first_seen_at=seen,
        last_seen_at=seen,
        last_run_id=run_id,
    )
    session.add(row)
    session.flush()
    return row


def _as_list(value):
    if isinstance(value, list):
        return value
    return [value] if isinstance(value, dict) else []


def enrich_proposition(client: httpx.Client, item: dict) -> dict:
    """Busca o processo detalhado mesmo quando a matéria veio primeiro de uma votação."""
    process_id = item.get("id")
    if not process_id and item.get("codigoMateria"):
        response = client.get(f"{BASE}/materia/{item['codigoMateria']}")
        response.raise_for_status()
        identification = (
            response.json()
            .get("DetalheMateria", {})
            .get("Materia", {})
            .get("IdentificacaoMateria", {})
        )
        process_id = identification.get("IdentificacaoProcesso")
    if not process_id:
        return item
    response = client.get(f"{BASE}/processo/{process_id}")
    response.raise_for_status()
    return {**item, "_detail": response.json()}


def upsert_proposition(session, item: dict, run_id: UUID, seen: datetime):
    detail = item.get("_detail", {})
    document = detail.get("documento", {})
    content = detail.get("conteudo", {})
    external_id = str(item.get("codigoMateria") or detail.get("codigoMateria") or item.get("id"))
    label = (
        item.get("identificacao")
        or detail.get("identificacao")
        or item.get("descricaoIdentificacaoMateria")
        or external_id
    )
    kind = (
        item.get("siglaSubtipoMateria")
        or detail.get("sigla")
        or item.get("sigla")
        or label.split(" ", 1)[0]
        or "MAT"
    )
    source_url = (
        f"{BASE}/processo/{detail.get('id')}"
        if detail.get("id")
        else f"{BASE}/materia/{external_id}"
    )
    record = source_record(
        session, run_id, "proposicao", external_id, source_url, detail or item, seen
    )
    row = session.scalar(
        select(Proposition).where(
            Proposition.source == SOURCE, Proposition.external_id == external_id
        )
    )
    if row is None:
        row = Proposition(source=SOURCE, external_id=external_id)
        session.add(row)
    number = item.get("numeroMateria") or detail.get("numero") or item.get("numero")
    year = item.get("anoMateria") or detail.get("ano") or item.get("ano")
    row.kind = kind
    row.number = int(number) if str(number or "").isdigit() else None
    row.year = int(year) if str(year or "").isdigit() else None
    row.summary = (
        content.get("ementa") or item.get("ementa") or item.get("Ementa") or label
    ).strip()
    row.presented_at = parse_date(
        document.get("dataApresentacao")
        or item.get("dataApresentacao")
        or item.get("DataApresentacao")
    )
    row.source_url, row.collected_at, row.source_record_id = source_url, seen, record.id
    session.flush()
    authors = _as_list(document.get("autoria")) + _as_list(detail.get("autoriaIniciativa"))
    if not authors:
        fallback = item.get("autoria") or item.get("Autor")
        authors = [{"autor": fallback}] if isinstance(fallback, str) else _as_list(fallback)
    for index, author in enumerate(authors):
        if isinstance(author, str):
            author = {"autor": author}
        if not isinstance(author, dict):
            continue
        name = author.get("autor") or author.get("NomeAutor")
        if not isinstance(name, str) or not name.strip():
            continue
        order = author.get("ordem", index + 1)
        legacy_key = f"{name}:{order}"
        official_id = str(author.get("codigoParlamentar", ""))
        verified = (
            author.get("siglaTipo") == "SENADOR"
            and author.get("casaEnte") == "SF"
            and official_id.isascii()
            and official_id.isdigit()
        )
        key = f"senador:{official_id}:{index + 1}" if verified else legacy_key
        existing = session.scalar(
            select(Authorship)
            .where(
                Authorship.proposition_id == row.id,
                Authorship.source == SOURCE,
                Authorship.author_key.in_((key, legacy_key)),
            )
            .order_by((Authorship.author_key == key).desc())
            .limit(1)
        )
        if existing is None:
            existing = Authorship(proposition_id=row.id, source=SOURCE)
            session.add(existing)
        existing.author_key = key
        existing.author_name = name
        existing.author_type = author.get("descricaoTipo") or author.get("DescricaoTipoAutor")
        existing.author_url = author.get("url")
        existing.source_url, existing.collected_at, existing.source_record_id = (
            source_url,
            seen,
            record.id,
        )
        existing.parliamentarian_id = (
            session.scalar(
                select(Parliamentarian.id).where(
                    Parliamentarian.source == SOURCE,
                    Parliamentarian.external_id == official_id,
                )
            )
            if verified
            else None
        )
        existing.signature_order = author.get("ordem") or author.get("NumOrdemAutor")
    for section in ("despachos", "autuacoes", "deliberacao", "ordensDoDia"):
        for index, event in enumerate(_as_list(detail.get(section))):
            event_key = f"{section}:{event.get('id', index)}"
            event_record = source_record(
                session, run_id, "tramitacao", f"{external_id}:{event_key}", source_url, event, seen
            )
            existing = session.scalar(
                select(ProceedingsEvent).where(
                    ProceedingsEvent.proposition_id == row.id,
                    ProceedingsEvent.source == SOURCE,
                    ProceedingsEvent.external_key == event_key,
                )
            )
            if existing is None:
                existing = ProceedingsEvent(
                    proposition_id=row.id, source=SOURCE, external_key=event_key
                )
                session.add(existing)
            occurred = event.get("data") or event.get("dataEvento") or event.get("dataDeliberacao")
            existing.occurred_at = parse_date(occurred)
            existing.sequence = index + 1
            existing.description = (
                event.get("descricao") or event.get("descricaoAcao") or event.get("tipo") or section
            )
            existing.situation = event.get("situacao") or event.get("descricaoSituacao")
            existing.dispatch = event.get("despacho") or event.get("observacao")
            existing.source_url, existing.collected_at, existing.source_record_id = (
                event_record.source_url,
                seen,
                event_record.id,
            )
    return row


def import_senado_legislation(engine, client=None):
    owns = client is None
    client = client or httpx.Client(
        timeout=httpx.Timeout(30, connect=8),
        follow_redirects=True,
        headers={"Accept": "application/json", "User-Agent": "DeOlhoNaPolitica/0.1"},
    )
    run_id, seen = uuid4(), now()
    try:
        with engine.connect() as lock:
            if not lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}):
                raise RuntimeError("Já existe uma importação legislativa do Senado em execução.")
            lock.commit()
            try:
                with Session(engine) as session, session.begin():
                    session.execute(
                        update(ImportRun)
                        .where(ImportRun.job == JOB, ImportRun.status == "running")
                        .values(status="interrupted", finished_at=seen, error_code="interrupted")
                    )
                    session.add(ImportRun(id=run_id, job=JOB, status="running", started_at=seen))
                process_response = client.get(f"{BASE}/processo")
                process_response.raise_for_status()
                if len(process_response.content) > MAX_PROCESS_BYTES:
                    raise RuntimeError("Resposta de processos excedeu o limite de tamanho.")
                processes = [
                    item for item in process_response.json() if item.get("tramitando") == "Sim"
                ]
                processes.sort(key=lambda item: item.get("dataSituacaoAtual") or "", reverse=True)
                processes = processes[:50]
                processes = [enrich_proposition(client, item) for item in processes]
                voting_year = local_today().year
                voting_response = client.get(f"{BASE}/plenario/votacao/nominal/{voting_year}")
                voting_response.raise_for_status()
                if len(voting_response.content) > MAX_VOTING_BYTES:
                    raise RuntimeError("Resposta de votações excedeu o limite de tamanho.")
                votings = (
                    voting_response.json()
                    .get("ListaVotacoes", {})
                    .get("Votacoes", {})
                    .get("Votacao", [])
                )
                votings = _as_list(votings)[-50:]
                with Session(engine) as session, session.begin():
                    propositions = {
                        str(item.get("codigoMateria")): upsert_proposition(
                            session, item, run_id, seen
                        )
                        for item in processes
                        if item.get("codigoMateria")
                    }
                    # Reprocessa matérias já conhecidas para corrigir registros mínimos
                    # criados anteriormente por uma votação sem o detalhe completo.
                    stale_props = session.scalars(
                        select(Proposition)
                        .where(Proposition.source == SOURCE)
                        .where(Proposition.presented_at.is_(None))
                        .order_by(Proposition.external_id)
                        .limit(10)
                    ).all()
                    for existing_prop in stale_props:
                        if existing_prop.external_id not in propositions:
                            enriched = enrich_proposition(
                                client, {"codigoMateria": existing_prop.external_id}
                            )
                            propositions[existing_prop.external_id] = upsert_proposition(
                                session, enriched, run_id, seen
                            )
                    for item in votings:
                        code = item.get("CodigoVotacaoSve") or item.get("CodigoSessaoVotacao")
                        if not code:
                            continue
                        voting_id = str(code)
                        record = source_record(
                            session,
                            run_id,
                            "votacao",
                            voting_id,
                            f"{BASE}/plenario/votacao/nominal/{voting_year}",
                            item,
                            seen,
                        )
                        row = session.scalar(
                            select(Voting).where(
                                Voting.source == SOURCE, Voting.external_id == voting_id
                            )
                        )
                        if row is None:
                            row = Voting(source=SOURCE, external_id=voting_id)
                            session.add(row)
                        row.occurred_on = (
                            date.fromisoformat(item["DataSessao"])
                            if item.get("DataSessao")
                            else None
                        )
                        row.description = item.get("DescricaoVotacao") or ""
                        row.object_description = item.get("DescricaoIdentificacaoMateria")
                        row.approved = {"A": True, "R": False}.get(item.get("Resultado"))
                        row.mode, row.source_url, row.collected_at, row.source_record_id = (
                            "nominal",
                            record.source_url,
                            seen,
                            record.id,
                        )
                        session.flush()
                        pid = str(item.get("CodigoMateria"))
                        prop = propositions.get(pid) or session.scalar(
                            select(Proposition).where(
                                Proposition.source == SOURCE, Proposition.external_id == pid
                            )
                        )
                        if prop is None and item.get("CodigoMateria"):
                            placeholder = {
                                "codigoMateria": pid,
                                "siglaSubtipoMateria": item.get("SiglaMateria"),
                                "numeroMateria": item.get("NumeroMateria"),
                                "anoMateria": item.get("AnoMateria"),
                                "identificacao": item.get("DescricaoIdentificacaoMateria"),
                            }
                            prop = upsert_proposition(
                                session, enrich_proposition(client, placeholder), run_id, seen
                            )
                        if (
                            prop
                            and session.get(VotingProposition, (row.id, prop.id, "object")) is None
                        ):
                            session.add(
                                VotingProposition(
                                    voting_id=row.id,
                                    proposition_id=prop.id,
                                    relation_type="object",
                                    source=SOURCE,
                                    source_url=record.source_url,
                                    collected_at=seen,
                                    source_record_id=record.id,
                                )
                            )
                        for vote in _as_list((item.get("Votos") or {}).get("VotoParlamentar")):
                            position = vote_position(vote.get("Voto"), vote.get("DescricaoVoto"))
                            if position is None:
                                continue
                            person = session.scalar(
                                select(Parliamentarian).where(
                                    Parliamentarian.source == SOURCE,
                                    Parliamentarian.external_id
                                    == str(vote.get("CodigoParlamentar")),
                                )
                            )
                            if person is None:
                                continue
                            existing = session.scalar(
                                select(Vote).where(
                                    Vote.voting_id == row.id, Vote.parliamentarian_id == person.id
                                )
                            )
                            if existing is None:
                                existing = Vote(voting_id=row.id, parliamentarian_id=person.id)
                                session.add(existing)
                            existing.position = position
                            existing.party_at_vote, existing.state_at_vote = vote.get(
                                "SiglaPartido"
                            ), vote.get("SiglaUF")
                            (
                                existing.source,
                                existing.source_url,
                                existing.collected_at,
                                existing.source_record_id,
                            ) = (SOURCE, record.source_url, seen, record.id)
                    run = session.get(ImportRun, run_id)
                    run.status, run.finished_at, run.received, run.inserted = (
                        "success",
                        now(),
                        len(processes) + len(votings),
                        len(processes) + len(votings),
                    )
                return {
                    "run_id": str(run_id),
                    "status": "success",
                    "propositions": len(processes),
                    "votings": len(votings),
                }
            except Exception as exc:
                with Session(engine) as session, session.begin():
                    run = session.get(ImportRun, run_id)
                    run.status, run.finished_at, run.error_code, run.error_message = (
                        "failed",
                        now(),
                        "processing_error",
                        type(exc).__name__,
                    )
                raise
            finally:
                lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY})
                lock.commit()
    finally:
        if owns:
            client.close()


if __name__ == "__main__":
    print(json.dumps(import_senado_legislation(get_engine()), ensure_ascii=False))
