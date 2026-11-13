"""Coleta detalhes públicos e histórico individual dos deputados da Câmara."""

import argparse
import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.integrations.camara.client import CamaraClient, SourceError
from app.integrations.camara.schemas import BASE_URL, DeputyProfile, DeputyStatus
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.parlamentares.models import Mandate, Parliamentarian

JOB = "camara.deputy_profiles"
SUPPLEMENT_JOB = "camara.deputy_history_supplement"
LOCK_KEY = 2810202612
PROFILE_NORMALIZER_VERSION = "deputy-profile-v2"
HISTORY_NORMALIZER_VERSION = "deputy-history-v1"
MAX_WORKERS = 3


class ImportBusy(Exception):
    pass


class ImportFailed(Exception):
    def __init__(self, run_id: UUID, code: str):
        self.run_id = run_id
        self.code = code
        super().__init__(f"Importação {run_id} falhou ({code}); consulte import_runs.")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalized(value: str | None) -> str:
    folded = unicodedata.normalize("NFKD", value or "")
    return "".join(char for char in folded if not unicodedata.combining(char)).casefold()


def exercise_period(statuses: list[DeputyStatus], legislature: str):
    """Usa apenas eventos explicitamente rotulados como entrada/saída pela Câmara."""
    events = sorted(
        (status for status in statuses if str(status.idLegislatura) == legislature),
        key=lambda status: status.dataHora,
    )
    transitions: list[tuple[str, datetime]] = []
    for status in events:
        description = normalized(status.descricaoStatus).strip()
        if description.startswith("entrada -"):
            transitions.append(("entry", status.dataHora))
        elif description.startswith("saida -"):
            transitions.append(("exit", status.dataHora))
    entries = [occurred_at for kind, occurred_at in transitions if kind == "entry"]
    started_on = min(entries).date() if entries else None
    ended_on = transitions[-1][1].date() if transitions and transitions[-1][0] == "exit" else None
    return started_on, ended_on


def source_record(
    session: Session,
    run_id: UUID,
    identifier: str,
    entity: str,
    source_url: str,
    normalizer_version: str,
    payload: dict,
    collected_at: datetime,
) -> SourceRecord:
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    record = session.scalar(
        select(SourceRecord).where(
            SourceRecord.source == "camara",
            SourceRecord.entity == entity,
            SourceRecord.external_id == identifier,
            SourceRecord.payload_hash == digest,
            SourceRecord.normalizer_version == normalizer_version,
        )
    )
    if record is None:
        record = SourceRecord(
            source="camara",
            entity=entity,
            external_id=identifier,
            source_url=source_url,
            payload_hash=digest,
            normalizer_version=normalizer_version,
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


def fetch_profile(client, person):
    try:
        profile, history = client.fetch_deputy_profile(int(person.external_id))
        return person.id, profile, history
    finally:
        # Limita cada trabalhador mesmo quando a fonte responde imediatamente.
        client.sleep(0.35)


def parse_firecrawl_history(path: Path) -> tuple[str, list[DeputyStatus]]:
    match = re.fullmatch(
        r"dadosabertos\.camara\.leg\.br-api-v2-deputados-([1-9][0-9]*)-historico\.md",
        path.name,
    )
    if match is None:
        raise SourceError(f"Nome de arquivo suplementar inválido: {path.name}")
    identifier = match.group(1)
    if path.stat().st_size > 2_000_000:
        raise SourceError(f"Arquivo suplementar excede o limite: {path.name}")
    try:
        wrapper = json.loads(path.read_text(encoding="utf-8"))
        raw_xml = wrapper["rawHtml"]
        if not isinstance(raw_xml, str):
            raise TypeError
        root = ET.fromstring(raw_xml)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ET.ParseError):
        raise SourceError(f"Arquivo suplementar incompatível: {path.name}") from None
    statuses = []
    for node in root.findall("./dados/statusParlamentar"):
        values = {child.tag: child.text for child in node}
        if values.get("id") != identifier:
            raise SourceError(f"ID divergente no arquivo suplementar: {path.name}")
        try:
            statuses.append(
                DeputyStatus(
                    id=int(identifier),
                    idLegislatura=int(values["idLegislatura"]),
                    dataHora=datetime.fromisoformat(values["dataHora"]),
                    situacao=values.get("situacao"),
                    descricaoStatus=values.get("descricaoStatus"),
                )
            )
        except (KeyError, TypeError, ValueError):
            raise SourceError(f"Evento inválido no arquivo suplementar: {path.name}") from None
    if not statuses:
        raise SourceError(f"Histórico suplementar vazio: {path.name}")
    return identifier, statuses


def history_payload(identifier: str, history: list[DeputyStatus]) -> dict:
    return {
        "id": int(identifier),
        "historico": [
            {
                "idLegislatura": status.idLegislatura,
                "dataHora": status.dataHora.isoformat(),
                "situacao": status.situacao,
                "descricaoStatus": status.descricaoStatus,
            }
            for status in history
        ],
    }


def is_individual_history_source(url: str) -> bool:
    return bool(
        re.fullmatch(
            rf"{re.escape(BASE_URL)}/deputados/[1-9][0-9]*/historico",
            url,
        )
    )


def import_camara_deputy_profiles(engine, client=None):
    client = client or CamaraClient()
    run_id = uuid4()
    collected_at = utc_now()
    try:
        with engine.connect() as lock:
            acquired = lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY})
            lock.commit()
            if not acquired:
                raise ImportBusy("Já existe uma importação de perfis de deputados em execução.")
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
                    people = session.scalars(
                        select(Parliamentarian)
                        .where(Parliamentarian.source == "camara")
                        .order_by(Parliamentarian.external_id)
                    ).all()
                bulk = hasattr(client, "fetch_deputy_profiles_bulk")
                if bulk:
                    profiles, histories = client.fetch_deputy_profiles_bulk()
                    missing = [
                        person.external_id
                        for person in people
                        if int(person.external_id) not in profiles
                    ]
                    if missing:
                        raise SourceError(
                            "Arquivo em lote não contém todos os perfis esperados: "
                            + ", ".join(missing[:10])
                        )
                    fetched = [
                        (
                            person.id,
                            profiles[int(person.external_id)],
                            histories.get(int(person.external_id), []),
                        )
                        for person in people
                    ]
                    profile_source_url = client.PROFILES_BULK_URL
                    history_source_url = client.HISTORY_BULK_URL
                else:
                    fetched_by_id = {}
                    pending = list(people)
                    last_errors: dict[str, str] = {}
                    for _round in range(3):
                        retry = []
                        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                            futures = {
                                executor.submit(fetch_profile, client, person): person
                                for person in pending
                            }
                            for future in as_completed(futures):
                                person = futures[future]
                                try:
                                    item = future.result()
                                except SourceError as exc:
                                    retry.append(person)
                                    last_errors[person.external_id] = str(exc)
                                else:
                                    fetched_by_id[person.id] = item
                        pending = retry
                        if not pending:
                            break
                        client.sleep(2)
                    if pending:
                        identifiers = ", ".join(person.external_id for person in pending[:10])
                        detail = last_errors.get(pending[0].external_id, "falha desconhecida")
                        raise SourceError(
                            f"Perfis indisponíveis após novas tentativas ({identifiers}): {detail}"
                        )
                    fetched = list(fetched_by_id.values())
                    profile_source_url = None
                    history_source_url = None

                inserted = updated = unchanged = 0
                with Session(engine) as session, session.begin():
                    for person_id, profile, history in fetched:
                        person = session.get(Parliamentarian, person_id)
                        profile_payload = {
                            "id": profile.id,
                            "nomeCivil": profile.nomeCivil,
                            "dataNascimento": (
                                profile.dataNascimento.isoformat()
                                if profile.dataNascimento
                                else None
                            ),
                        }
                        profile_record = source_record(
                            session,
                            run_id,
                            person.external_id,
                            "perfil_deputado",
                            profile_source_url or f"{BASE_URL}/deputados/{person.external_id}",
                            PROFILE_NORMALIZER_VERSION,
                            profile_payload,
                            collected_at,
                        )
                        changed = (
                            person.birth_date != profile.dataNascimento
                            or person.profile_source_record_id != profile_record.id
                        )
                        first_profile = person.profile_source_record_id is None
                        person.birth_date = profile.dataNascimento
                        person.profile_collected_at = collected_at
                        person.profile_source_record_id = profile_record.id
                        if history:
                            history_record = source_record(
                                session,
                                run_id,
                                person.external_id,
                                "historico_deputado",
                                history_source_url
                                or f"{BASE_URL}/deputados/{person.external_id}/historico",
                                HISTORY_NORMALIZER_VERSION,
                                history_payload(person.external_id, history),
                                collected_at,
                            )
                            for mandate in session.scalars(
                                select(Mandate).where(Mandate.parliamentarian_id == person.id)
                            ):
                                # O arquivo em lote de histórico pode estar atrasado. Uma
                                # resposta individual já publicada sempre tem precedência.
                                if history_source_url and is_individual_history_source(
                                    mandate.source_url
                                ):
                                    continue
                                started_on, ended_on = exercise_period(
                                    history, mandate.legislature_external_id
                                )
                                if (mandate.started_on, mandate.ended_on) != (
                                    started_on,
                                    ended_on,
                                ):
                                    changed = True
                                mandate.started_on = started_on
                                mandate.ended_on = ended_on
                                mandate.source_url = history_record.source_url
                                mandate.source_record_id = history_record.id
                                mandate.collected_at = collected_at
                        if first_profile:
                            inserted += 1
                        elif changed:
                            updated += 1
                        else:
                            unchanged += 1
                    run = session.get(ImportRun, run_id)
                    run.status = "success"
                    run.finished_at = utc_now()
                    run.pages = 2 if bulk else len(fetched) * 2
                    run.received = len(fetched)
                    run.inserted = inserted
                    run.updated = updated
                    run.unchanged = unchanged
                return {
                    "run_id": str(run_id),
                    "status": "success",
                    "received": len(fetched),
                    "history_covered": sum(bool(history) for _, _, history in fetched),
                    "inserted": inserted,
                    "updated": updated,
                    "unchanged": unchanged,
                }
            except Exception as exc:
                code = "source_error" if isinstance(exc, SourceError) else "processing_error"
                with Session(engine) as session, session.begin():
                    run = session.get(ImportRun, run_id)
                    if run:
                        run.status = "failed"
                        run.finished_at = utc_now()
                        run.error_code = code
                        run.error_message = (
                            str(exc)[:500]
                            if isinstance(exc, SourceError)
                            else "Erro interno; publicação revertida."
                        )
                raise ImportFailed(run_id, code) from None
            finally:
                lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY})
                lock.commit()
    finally:
        client.close()


def import_camara_deputy_history_files(engine, directory: Path):
    paths = sorted(
        directory.glob("dadosabertos.camara.leg.br-api-v2-deputados-*-historico.md")
    )
    if not paths:
        raise SourceError("Nenhum arquivo suplementar de histórico encontrado.")
    parsed = [parse_firecrawl_history(path) for path in paths]
    if len({identifier for identifier, _ in parsed}) != len(parsed):
        raise SourceError("Histórico suplementar contém IDs duplicados.")
    run_id = uuid4()
    collected_at = utc_now()
    with engine.connect() as lock:
        acquired = lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY})
        lock.commit()
        if not acquired:
            raise ImportBusy("Já existe uma importação de perfis de deputados em execução.")
        try:
            with Session(engine) as session, session.begin():
                session.execute(
                    update(ImportRun)
                    .where(ImportRun.job == SUPPLEMENT_JOB, ImportRun.status == "running")
                    .values(
                        status="interrupted",
                        finished_at=collected_at,
                        error_code="interrupted",
                    )
                )
                session.add(
                    ImportRun(
                        id=run_id,
                        job=SUPPLEMENT_JOB,
                        status="running",
                        started_at=collected_at,
                    )
                )
            updated = unchanged = 0
            with Session(engine) as session, session.begin():
                for identifier, history in parsed:
                    person = session.scalar(
                        select(Parliamentarian).where(
                            Parliamentarian.source == "camara",
                            Parliamentarian.external_id == identifier,
                        )
                    )
                    if person is None:
                        raise SourceError(f"Histórico sem deputado correspondente: {identifier}")
                    record = source_record(
                        session,
                        run_id,
                        identifier,
                        "historico_deputado",
                        f"{BASE_URL}/deputados/{identifier}/historico",
                        HISTORY_NORMALIZER_VERSION,
                        history_payload(identifier, history),
                        collected_at,
                    )
                    changed = False
                    for mandate in session.scalars(
                        select(Mandate).where(Mandate.parliamentarian_id == person.id)
                    ):
                        started_on, ended_on = exercise_period(
                            history, mandate.legislature_external_id
                        )
                        if (
                            mandate.started_on,
                            mandate.ended_on,
                            mandate.source_record_id,
                        ) != (started_on, ended_on, record.id):
                            changed = True
                        mandate.started_on = started_on
                        mandate.ended_on = ended_on
                        mandate.source_url = record.source_url
                        mandate.source_record_id = record.id
                        mandate.collected_at = collected_at
                    updated += int(changed)
                    unchanged += int(not changed)
                run = session.get(ImportRun, run_id)
                run.status = "success"
                run.finished_at = utc_now()
                run.pages = len(parsed)
                run.received = len(parsed)
                run.updated = updated
                run.unchanged = unchanged
            return {
                "run_id": str(run_id),
                "status": "success",
                "received": len(parsed),
                "updated": updated,
                "unchanged": unchanged,
            }
        except Exception as exc:
            with Session(engine) as session, session.begin():
                run = session.get(ImportRun, run_id)
                if run:
                    run.status = "failed"
                    run.finished_at = utc_now()
                    run.error_code = (
                        "source_error" if isinstance(exc, SourceError) else "processing_error"
                    )
                    run.error_message = (
                        str(exc)[:500]
                        if isinstance(exc, SourceError)
                        else "Erro interno; publicação revertida."
                    )
            raise ImportFailed(
                run_id, "source_error" if isinstance(exc, SourceError) else "processing_error"
            ) from None
        finally:
            lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY})
            lock.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--supplemental-history-dir",
        type=Path,
        help="Diretório local com respostas rawHtml do Firecrawl para backfill controlado.",
    )
    args = parser.parse_args()
    try:
        result = (
            import_camara_deputy_history_files(get_engine(), args.supplemental_history_dir)
            if args.supplemental_history_dir
            else import_camara_deputy_profiles(get_engine())
        )
        print(json.dumps(result, ensure_ascii=False))
    except (ImportBusy, ImportFailed, SourceError) as exc:
        print(json.dumps({"status": "failed", "message": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
