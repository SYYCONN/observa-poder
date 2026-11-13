"""Importa uma janela limitada de proposições e votações da Câmara."""

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.integrations.legislation import camara_boolean, legislative_datetime, vote_position
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.parlamentares.models import Parliamentarian
from app.modules.proposicoes.linking import find_parliamentarian
from app.modules.proposicoes.models import Authorship, ProceedingsEvent, Proposition
from app.modules.votacoes.models import Vote, Voting, VotingProposition

BASE = "https://dadosabertos.camara.leg.br/api/v2"
JOB = "camara.recent_legislation"
LOCK_KEY = 2810202602
LIMIT = 20
BACKFILL_LIMIT = 12


def get_json(client, url, **kwargs):
    """Consulta a API da Câmara com retentativas para falhas transitórias."""
    for attempt in range(3):
        try:
            response = client.get(url, **kwargs)
        except httpx.TransportError:
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
        if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
            time.sleep(1.5 * (attempt + 1))
            continue
        response.raise_for_status()
        return response.json()
    raise RuntimeError("A API da Câmara não respondeu após as retentativas.")


def now():
    return datetime.now(timezone.utc)


def dt(value):
    return legislative_datetime(value)


def record(
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
    version = "legislacao-v1"
    current = session.scalar(
        select(SourceRecord).where(
            SourceRecord.source == "camara",
            SourceRecord.entity == entity,
            SourceRecord.external_id == external_id,
            SourceRecord.payload_hash == digest,
            SourceRecord.normalizer_version == version,
        )
    )
    if current:
        current.last_seen_at, current.last_run_id = seen, run_id
        return current
    current = SourceRecord(
        source="camara",
        entity=entity,
        external_id=external_id,
        source_url=url,
        payload_hash=digest,
        normalizer_version=version,
        payload=payload,
        first_seen_at=seen,
        last_seen_at=seen,
        last_run_id=run_id,
    )
    session.add(current)
    session.flush()
    return current


def upsert_proposition(session, item, run_id, seen):
    external_id = str(item["id"])
    source_url = item.get("uri") or f"{BASE}/proposicoes/{external_id}"
    source = record(session, run_id, "proposicao", external_id, source_url, item, seen)
    row = session.scalar(
        select(Proposition).where(
            Proposition.source == "camara", Proposition.external_id == external_id
        )
    )
    if row is None:
        row = Proposition(source="camara", external_id=external_id)
        session.add(row)
    row.kind = item.get("siglaTipo") or "DESCONHECIDO"
    row.number = item.get("numero")
    row.year = item.get("ano")
    row.summary = item.get("ementa") or ""
    row.detailed_summary = item.get("ementaDetalhada") or None
    row.full_text_url = item.get("urlInteiroTeor") or None
    raw_keywords = item.get("keywords")
    if isinstance(raw_keywords, str):
        row.keywords = [
            keyword.strip() for keyword in re.split(r"[,;]", raw_keywords) if keyword.strip()
        ]
    elif isinstance(raw_keywords, list):
        row.keywords = [str(keyword).strip() for keyword in raw_keywords if str(keyword).strip()]
    else:
        row.keywords = None
    status = item.get("statusProposicao") or {}
    row.status_description = status.get("descricaoSituacao") or status.get("descricaoTramitacao")
    row.status_agency = status.get("siglaOrgao")
    row.status_appreciation = status.get("apreciacao")
    row.status_regime = status.get("regime")
    row.status_at = dt(status.get("dataHora"))
    if "statusProposicao" in item or "urlInteiroTeor" in item:
        row.official_detail_collected_at = seen
    row.presented_at = dt(item.get("dataApresentacao"))
    row.source_url, row.collected_at, row.source_record_id = source_url, seen, source.id
    session.flush()
    return row


def upsert_authorships(session, proposition, authors, run_id, seen):
    for author in authors:
        key = author.get("uri") or author.get("nome")
        if not key or not author.get("nome"):
            continue
        source = record(
            session,
            run_id,
            "autor",
            f"{proposition.external_id}:{key}",
            f"{BASE}/proposicoes/{proposition.external_id}/autores",
            author,
            seen,
        )
        existing = session.scalar(
            select(Authorship).where(
                Authorship.proposition_id == proposition.id,
                Authorship.source == "camara",
                Authorship.author_key == key,
            )
        )
        if existing is None:
            existing = Authorship(proposition_id=proposition.id, source="camara", author_key=key)
            session.add(existing)
        existing.author_name = author["nome"]
        existing.author_type = author.get("tipo")
        existing.author_url = author.get("uri")
        existing.source_url = source.source_url
        existing.collected_at = seen
        existing.source_record_id = source.id
        person = find_parliamentarian(session, "camara", existing.author_name, existing.author_url)
        existing.parliamentarian_id = person.id if person else None
        existing.signature_order = author.get("ordemAssinatura")
        existing.is_proponent = camara_boolean(author.get("proponente"))


def enrich_known_proposition(session, client, item, run_id, seen):
    external_id = str(item["id"])
    detail = get_json(client, f"{BASE}/proposicoes/{external_id}").get("dados", {})
    proposition = upsert_proposition(session, {**item, **detail}, run_id, seen)
    authors = get_json(client, f"{BASE}/proposicoes/{external_id}/autores").get("dados", [])
    upsert_authorships(session, proposition, authors, run_id, seen)
    return proposition


def import_legislation(engine, limit=LIMIT, backfill_limit=BACKFILL_LIMIT, client=None):
    owns = client is None
    client = client or httpx.Client(
        timeout=httpx.Timeout(20, connect=5),
        headers={"Accept": "application/json", "User-Agent": "DeOlhoNaPolitica/0.1"},
    )
    run_id = uuid4()
    seen = now()
    try:
        with engine.connect() as lock:
            if not lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}):
                raise RuntimeError("Já existe uma importação legislativa em execução.")
            lock.commit()
            try:
                with Session(engine) as session, session.begin():
                    session.execute(
                        update(ImportRun)
                        .where(ImportRun.job == JOB, ImportRun.status == "running")
                        .values(status="interrupted", finished_at=seen, error_code="interrupted")
                    )
                    session.add(ImportRun(id=run_id, job=JOB, status="running", started_at=seen))
                propositions = get_json(
                    client,
                    f"{BASE}/proposicoes",
                    params={"pagina": 1, "itens": limit, "ordem": "DESC", "ordenarPor": "id"},
                ).get("dados", [])
                votings = get_json(
                    client,
                    f"{BASE}/votacoes",
                    params={
                        "pagina": 1,
                        "itens": limit,
                        "ordem": "DESC",
                        "ordenarPor": "dataHoraRegistro",
                    },
                ).get("dados", [])
                with Session(engine) as session, session.begin():
                    proposition_rows = {}
                    for item in propositions:
                        row = enrich_known_proposition(session, client, item, run_id, seen)
                        proposition_rows[str(item["id"])] = row
                        for event in get_json(
                            client, f"{BASE}/proposicoes/{item['id']}/tramitacoes"
                        ).get("dados", []):
                            key = str(event.get("sequencia"))
                            er = record(
                                session,
                                run_id,
                                "tramitacao",
                                f"{item['id']}:{key}",
                                f"{BASE}/proposicoes/{item['id']}/tramitacoes",
                                event,
                                seen,
                            )
                            existing = session.scalar(
                                select(ProceedingsEvent).where(
                                    ProceedingsEvent.proposition_id == row.id,
                                    ProceedingsEvent.source == "camara",
                                    ProceedingsEvent.external_key == key,
                                )
                            )
                            if existing is None:
                                existing = ProceedingsEvent(
                                    proposition_id=row.id, source="camara", external_key=key
                                )
                                session.add(existing)
                            existing.occurred_at, existing.sequence = dt(
                                event.get("dataHora")
                            ), event.get("sequencia")
                            (
                                existing.agency_url,
                                existing.description,
                                existing.situation,
                                existing.dispatch,
                                existing.rapporteur_url,
                            ) = (
                                event.get("uriOrgao"),
                                event.get("descricaoTramitacao"),
                                event.get("descricaoSituacao"),
                                event.get("despacho"),
                                event.get("uriUltimoRelator"),
                            )
                            (
                                existing.source_url,
                                existing.collected_at,
                                existing.source_record_id,
                            ) = (er.source_url, seen, er.id)
                    recent_ids = {str(item["id"]) for item in propositions}
                    backfill = session.scalars(
                        select(Proposition)
                        .where(
                            Proposition.source == "camara",
                            Proposition.external_id.not_in(recent_ids),
                            Proposition.official_detail_collected_at.is_(None),
                        )
                        .order_by(Proposition.presented_at.desc().nullslast(), Proposition.id)
                        .limit(backfill_limit)
                    ).all()
                    for stale in backfill:
                        proposition_rows[stale.external_id] = enrich_known_proposition(
                            session,
                            client,
                            {
                                "id": int(stale.external_id),
                                "uri": stale.source_url,
                                "siglaTipo": stale.kind,
                                "numero": stale.number,
                                "ano": stale.year,
                                "ementa": stale.summary,
                            },
                            run_id,
                            seen,
                        )
                    for item in votings:
                        vid = str(item["id"])
                        detail = get_json(client, f"{BASE}/votacoes/{vid}").get("dados", {})
                        vr = record(
                            session,
                            run_id,
                            "votacao",
                            vid,
                            item.get("uri") or f"{BASE}/votacoes/{vid}",
                            detail or item,
                            seen,
                        )
                        row = session.scalar(
                            select(Voting).where(
                                Voting.source == "camara", Voting.external_id == vid
                            )
                        )
                        if row is None:
                            row = Voting(source="camara", external_id=vid)
                            session.add(row)
                        row.occurred_on = dt(item.get("data")).date() if item.get("data") else None
                        row.registered_at = dt(item.get("dataHoraRegistro"))
                        row.description = item.get("descricao") or ""
                        row.object_description = detail.get("descUltimaAberturaVotacao")
                        row.agency_url = item.get("uriOrgao")
                        row.approved = camara_boolean(item.get("aprovacao"))
                        row.source_url, row.collected_at, row.source_record_id = (
                            item.get("uri") or f"{BASE}/votacoes/{vid}",
                            seen,
                            vr.id,
                        )
                        session.flush()
                        objects = detail.get("objetosPossiveis", [])
                        if detail.get("ultimaApresentacaoProposicao", {}).get(
                            "uriProposicaoCitada"
                        ):
                            objects.append(
                                {
                                    "uri": detail["ultimaApresentacaoProposicao"][
                                        "uriProposicaoCitada"
                                    ]
                                }
                            )
                        for obj in objects:
                            pid = str(
                                obj.get("id") or obj.get("uri", "").rstrip("/").split("/")[-1]
                            )
                            if not pid.isdigit():
                                continue
                            prop = proposition_rows.get(pid) or session.scalar(
                                select(Proposition).where(
                                    Proposition.source == "camara", Proposition.external_id == pid
                                )
                            )
                            if prop is None and obj.get("siglaTipo"):
                                prop = upsert_proposition(
                                    session,
                                    {
                                        "id": int(pid),
                                        "uri": obj.get("uri") or f"{BASE}/proposicoes/{pid}",
                                        "siglaTipo": obj.get("siglaTipo"),
                                        "numero": obj.get("numero"),
                                        "ano": obj.get("ano"),
                                        "ementa": obj.get("ementa") or "",
                                        "dataApresentacao": obj.get("dataApresentacao"),
                                    },
                                    run_id,
                                    seen,
                                )
                            if prop is None:
                                continue
                            relation = (
                                "object"
                                if obj.get("id") == item.get("proposicaoObjeto")
                                else "possible_object"
                            )
                            exists = session.get(VotingProposition, (row.id, prop.id, relation))
                            if exists is None:
                                session.add(
                                    VotingProposition(
                                        voting_id=row.id,
                                        proposition_id=prop.id,
                                        relation_type=relation,
                                        source="camara",
                                        source_url=vr.source_url,
                                        collected_at=seen,
                                        source_record_id=vr.id,
                                    )
                                )
                        for vote in get_json(client, f"{BASE}/votacoes/{vid}/votos").get(
                            "dados", []
                        ):
                            position = vote_position(vote.get("voto"), vote.get("tipoVoto"))
                            if position is None:
                                continue
                            row.mode = "nominal"
                            person = session.scalar(
                                select(Parliamentarian).where(
                                    Parliamentarian.source == "camara",
                                    Parliamentarian.external_id
                                    == str(
                                        vote.get("deputado_", {}).get("id")
                                        or vote.get("deputado", {}).get("id")
                                    ),
                                )
                            )
                            if not person:
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
                            existing.party_at_vote = vote.get("deputado_", {}).get(
                                "siglaPartido"
                            ) or vote.get("deputado", {}).get("siglaPartido")
                            existing.state_at_vote = vote.get("deputado_", {}).get(
                                "siglaUf"
                            ) or vote.get("deputado", {}).get("siglaUf")
                            (
                                existing.source,
                                existing.source_url,
                                existing.collected_at,
                                existing.source_record_id,
                            ) = ("camara", vr.source_url, seen, vr.id)
                    run = session.get(ImportRun, run_id)
                    run.status, run.finished_at, run.received, run.inserted = (
                        "success",
                        now(),
                        len(propositions) + len(votings) + len(backfill),
                        len(propositions) + len(votings),
                    )
                return {
                    "run_id": str(run_id),
                    "status": "success",
                    "propositions": len(propositions),
                    "propositions_enriched": len(backfill),
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
    print(json.dumps(import_legislation(get_engine()), ensure_ascii=False))
