import hashlib
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.camara.schemas import BASE_URL, Deputy
from app.integrations.senado.client import BASE_URL as SENADO_BASE_URL, Senator
from app.modules.coletas.models import SourceRecord
from app.modules.parlamentares.models import Mandate, MandateObservation, Parliamentarian

SOURCE = "camara"
NORMALIZER_VERSION = "deputados-v1"
SENADO_SOURCE = "senado"
SENADO_NORMALIZER_VERSION = "senadores-v1"


def persist_deputies(
    session: Session, deputies: list[Deputy], run_id: UUID, observed_at: datetime
) -> dict[str, int]:
    """O chamador controla a transação. Não há commits parciais ou remoção de ausentes."""
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}
    for deputy in deputies:
        # Lista permitida: não armazenar email, CPF, gabinete ou demais campos extras.
        payload = deputy.model_dump()
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
        record = session.scalar(
            select(SourceRecord).where(
                SourceRecord.source == SOURCE,
                SourceRecord.entity == "deputado",
                SourceRecord.external_id == str(deputy.id),
                SourceRecord.payload_hash == digest,
                SourceRecord.normalizer_version == NORMALIZER_VERSION,
            )
        )
        if record is None:
            record = SourceRecord(
                source=SOURCE,
                entity="deputado",
                external_id=str(deputy.id),
                source_url=f"{BASE_URL}/deputados?pagina={deputy._page_number}&itens=100&ordem=ASC&ordenarPor=id",
                payload_hash=digest,
                normalizer_version=NORMALIZER_VERSION,
                payload=payload,
                first_seen_at=observed_at,
                last_seen_at=observed_at,
                last_run_id=run_id,
            )
            session.add(record)
            session.flush()
        else:
            record.last_seen_at = observed_at
            record.last_run_id = run_id
        person = session.scalar(
            select(Parliamentarian).where(
                Parliamentarian.source == SOURCE,
                Parliamentarian.external_id == str(deputy.id),
            )
        )
        inserted = person is None
        changed = inserted or person.source_record_id != record.id
        if person is None:
            person = Parliamentarian(source=SOURCE, external_id=str(deputy.id))
            session.add(person)
        person.name = deputy.nome
        person.photo_url = deputy.urlFoto
        person.is_current = True
        person.source_url = deputy.uri
        person.source_record_id = record.id
        person.collected_at = observed_at
        session.flush()
        mandate = session.scalar(
            select(Mandate).where(
                Mandate.parliamentarian_id == person.id,
                Mandate.source == SOURCE,
                Mandate.legislature_external_id == str(deputy.idLegislatura),
            )
        )
        mandate_changed = mandate is None or (
            mandate.state,
            mandate.party,
            mandate.party_source_url,
        ) != (deputy.siglaUf, deputy.siglaPartido, deputy.uriPartido)
        if mandate is None:
            mandate = Mandate(
                parliamentarian_id=person.id,
                source=SOURCE,
                legislature_external_id=str(deputy.idLegislatura),
            )
            session.add(mandate)
        mandate.state = deputy.siglaUf
        mandate.party = deputy.siglaPartido
        mandate.party_source_url = deputy.uriPartido
        mandate.source_url = deputy.uri
        mandate.source_record_id = record.id
        mandate.collected_at = observed_at
        session.flush()
        if mandate_changed:
            session.add(
                MandateObservation(
                    mandate_id=mandate.id,
                    run_id=run_id,
                    source_record_id=record.id,
                    observed_at=observed_at,
                    state=mandate.state,
                    party=mandate.party,
                    party_source_url=mandate.party_source_url,
                )
            )
        counts[
            "inserted" if inserted else "updated" if changed or mandate_changed else "unchanged"
        ] += 1
    return counts


def persist_senators(
    session: Session, senators: list[Senator], run_id: UUID, observed_at: datetime
) -> dict[str, int]:
    """Publica a lista completa do Senado dentro da transação do chamador."""
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}
    for senator in senators:
        payload = senator.payload()
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
        record = session.scalar(
            select(SourceRecord).where(
                SourceRecord.source == SENADO_SOURCE,
                SourceRecord.entity == "senador",
                SourceRecord.external_id == senator.external_id,
                SourceRecord.payload_hash == digest,
                SourceRecord.normalizer_version == SENADO_NORMALIZER_VERSION,
            )
        )
        if record is None:
            record = SourceRecord(
                source=SENADO_SOURCE,
                entity="senador",
                external_id=senator.external_id,
                source_url=SENADO_BASE_URL,
                payload_hash=digest,
                normalizer_version=SENADO_NORMALIZER_VERSION,
                payload=payload,
                first_seen_at=observed_at,
                last_seen_at=observed_at,
                last_run_id=run_id,
            )
            session.add(record)
            session.flush()
        else:
            record.last_seen_at = observed_at
            record.last_run_id = run_id
        person = session.scalar(
            select(Parliamentarian).where(
                Parliamentarian.source == SENADO_SOURCE,
                Parliamentarian.external_id == senator.external_id,
            )
        )
        inserted = person is None
        changed = inserted or not person.is_current or person.source_record_id != record.id
        if person is None:
            person = Parliamentarian(source=SENADO_SOURCE, external_id=senator.external_id)
            session.add(person)
        person.name = senator.name
        person.photo_url = senator.photo_url
        person.is_current = True
        person.source_url = senator.source_url
        person.source_record_id = record.id
        person.collected_at = observed_at
        session.flush()
        mandate = session.scalar(
            select(Mandate).where(
                Mandate.parliamentarian_id == person.id,
                Mandate.source == SENADO_SOURCE,
                Mandate.legislature_external_id == senator.legislature,
            )
        )
        mandate_changed = mandate is None or (
            mandate.state,
            mandate.party,
            mandate.party_source_url,
            mandate.started_on,
            mandate.ended_on,
        ) != (
            senator.state,
            senator.party,
            senator.source_url,
            None,
            None,
        )
        if mandate is None:
            mandate = Mandate(
                parliamentarian_id=person.id,
                source=SENADO_SOURCE,
                legislature_external_id=senator.legislature,
            )
            session.add(mandate)
        mandate.state = senator.state
        mandate.party = senator.party
        mandate.party_source_url = senator.source_url
        # A lista informa datas da legislatura, não o exercício individual do senador.
        # Também corrige datas inferidas por versões anteriores deste coletor.
        mandate.started_on = None
        mandate.ended_on = None
        mandate.source_url = senator.source_url
        mandate.source_record_id = record.id
        mandate.collected_at = observed_at
        session.flush()
        if mandate_changed:
            session.add(
                MandateObservation(
                    mandate_id=mandate.id,
                    run_id=run_id,
                    source_record_id=record.id,
                    observed_at=observed_at,
                    state=mandate.state,
                    party=mandate.party,
                    party_source_url=mandate.party_source_url,
                )
            )
        counts[
            "inserted" if inserted else "updated" if changed or mandate_changed else "unchanged"
        ] += 1
    return counts
