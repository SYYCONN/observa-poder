import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
import httpx
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.db import models
from app.db.base import Base
from app.jobs.recover_public_snapshot import export_snapshot, recover_snapshot
from app.jobs.import_legislation import import_legislation
from app.jobs.import_senado_legislation import upsert_proposition
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.financas.models import ParliamentaryStaffMember, ParliamentaryStaffSummary
from app.modules.parlamentares.models import Parliamentarian
from app.modules.proposicoes.models import Proposition


@pytest.fixture
def databases():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Execute scripts/test_backend.py para PostgreSQL isolado.")
    root = create_engine(url)
    schemas = ["recovery_" + uuid4().hex for _ in range(2)]
    engines = []
    try:
        for schema in schemas:
            with root.begin() as conn:
                conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            engine = root.execution_options(schema_translate_map={None: schema})
            Base.metadata.create_all(engine)
            seed(engine)
            engines.append(engine)
        yield engines
    finally:
        with root.begin() as conn:
            for schema in schemas:
                conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        root.dispose()


def seed(engine):
    seen = datetime(2026, 10, 31, tzinfo=timezone.utc)
    with Session(engine) as session, session.begin():
        run = ImportRun(job="fixture", status="success", started_at=seen)
        session.add(run)
        session.flush()
        origin = SourceRecord(
            source="camara", entity="fixture", external_id="1", payload={},
            payload_hash="a" * 64, normalizer_version="fixture",
            source_url="https://www.camara.leg.br/", first_seen_at=seen,
            last_seen_at=seen, last_run_id=run.id,
        )
        session.add(origin)
        session.flush()
        session.add(Parliamentarian(
            source="camara", external_id="1", name="Pessoa de teste",
            source_url=origin.source_url, collected_at=seen, source_record_id=origin.id,
        ))


def package(source):
    with Session(source) as session, session.begin():
        person = session.scalars(select(Parliamentarian)).one()
        provenance = dict(source="camara", source_url=person.source_url,
                          source_record_id=person.source_record_id, collected_at=person.collected_at)
        session.add(Proposition(external_id="11", kind="PL", year=2026, number=11,
                                summary="Ementa local", **provenance))
        session.add(ParliamentaryStaffSummary(
            parliamentarian_id=person.id, year=2026, month=10, staff_count=1,
            source_query_url=person.source_url, **provenance,
        ))
        session.add(ParliamentaryStaffMember(
            external_id="assessor-1", parliamentarian_id=person.id, year=2026, month=10,
            name="Equipe de teste", gross_amount=Decimal("100.00"),
            source_query_url=person.source_url, **provenance,
        ))
    return json.loads(json.dumps(export_snapshot(source), default=str))


def test_recovery_remaps_ids_preserves_existing_data_and_is_idempotent(databases):
    source, target = databases
    bundle = package(source)
    with Session(target) as session, session.begin():
        person = session.scalars(select(Parliamentarian)).one()
        person_id = person.id
        session.add(Proposition(
            source="camara", external_id="11", kind="PL", year=2026, number=11,
            summary="Ementa atual em produção", source_url=person.source_url,
            source_record_id=person.source_record_id, collected_at=person.collected_at,
        ))
    rehearsal = recover_snapshot(target, bundle)
    assert rehearsal["applied"] is False
    with Session(target) as session:
        assert session.scalar(select(func.count()).select_from(ParliamentaryStaffMember)) == 0
    first = recover_snapshot(target, bundle, apply=True)
    second = recover_snapshot(target, bundle, apply=True)
    assert first["counts"]["parliamentary_staff_members"]["inserted"] == 1
    assert second["counts"]["parliamentary_staff_members"]["inserted"] == 0
    with Session(target) as session:
        member = session.scalars(select(ParliamentaryStaffMember)).one()
        assert member.parliamentarian_id == person_id
        assert member.gross_amount == Decimal("100.00")
        assert session.scalars(select(Proposition)).one().summary == "Ementa atual em produção"
        origin = session.get(SourceRecord, member.source_record_id)
        assert "original_payload_hash" in origin.payload


def test_recovery_rolls_back_all_tables_on_a_broken_reference(databases):
    source, target = databases
    bundle = package(source)
    bundle["tables"]["parliamentary_staff_members"][0]["parliamentarian_id"] = str(uuid4())
    with pytest.raises(KeyError):
        recover_snapshot(target, bundle, apply=True)
    with Session(target) as session:
        assert session.scalar(select(func.count()).select_from(Proposition)) == 0
        assert session.scalar(select(func.count()).select_from(ParliamentaryStaffSummary)) == 0
        assert session.scalar(select(func.count()).select_from(SourceRecord)) == 1


def test_missing_camara_proposition_does_not_prevent_valid_import(databases):
    _, engine = databases

    def handler(request):
        path = request.url.path
        if path.endswith("/proposicoes"):
            return httpx.Response(200, json={"dados": [{"id": 404}, {"id": 11}]})
        if path.endswith("/proposicoes/404"):
            return httpx.Response(404)
        if path.endswith("/proposicoes/11"):
            return httpx.Response(200, json={"dados": {
                "id": 11, "siglaTipo": "PL", "ano": 2026, "numero": 11, "ementa": "Teste",
            }})
        return httpx.Response(200, json={"dados": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = import_legislation(engine, client=client)
    assert result["status"] == "success"
    assert result["unavailable_propositions"] == ["404"]
    with Session(engine) as session:
        assert session.scalars(select(Proposition)).one().external_id == "11"
        assert session.scalar(select(func.count()).select_from(SourceRecord).where(
            SourceRecord.entity == "proposicao_indisponivel"
        )) == 1


def test_senado_detail_exposes_official_text_status_and_keywords(databases):
    _, engine = databases
    seen = datetime(2026, 11, 17, tzinfo=timezone.utc)
    with Session(engine) as session, session.begin():
        run = ImportRun(job="fixture", status="success", started_at=seen)
        session.add(run)
        session.flush()
        row = upsert_proposition(session, {
            "codigoMateria": 99,
            "_detail": {
                "id": 99, "numero": 10, "ano": 2026, "sigla": "PL",
                "situacaoAtual": "Em tramitação", "dataSituacaoAtual": "2026-11-17",
                "documento": {
                    "url": "https://legis.senado.leg.br/documento/99",
                    "indexacao": "SAÚDE, ORÇAMENTO",
                },
                "conteudo": {"ementa": "Ementa oficial"},
            },
        }, run.id, seen)
        assert row.full_text_url == "https://legis.senado.leg.br/documento/99"
        assert row.status_description == "Em tramitação"
        assert row.keywords == ["SAÚDE", "ORÇAMENTO"]
        assert row.official_detail_collected_at == seen
