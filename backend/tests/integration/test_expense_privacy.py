"""Confere minimização no caminho real de importação, sem acessar a Câmara."""

import hashlib
import io
import json
import os
import zipfile
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.db import models  # noqa: F401 — registra todas as tabelas
from app.db.base import Base
from app.jobs.import_camara_expenses import (
    JOB,
    ExpenseImportFailed,
    ExpenseSourceError,
    import_camara_expenses,
    official_camara_document_url,
    open_expense_file,
)
from app.jobs.import_deputies import import_deputies
from app.integrations.camara.schemas import BASE_URL, Deputy
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.financas.models import ParliamentaryExpense


@pytest.fixture
def engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Execute scripts/test_backend.py para PostgreSQL isolado.")
    root = create_engine(url)
    schema = "test_" + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = root.execution_options(schema_translate_map={None: schema})
    Base.metadata.create_all(scoped)
    try:
        yield scoped, schema
    finally:
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


class DeputiesClient:
    pages = received = 1

    def close(self):
        pass

    def fetch_current_deputies(self):
        return [Deputy(id=123, uri=f"{BASE_URL}/deputados/123", nome="Pessoa de teste",
                       siglaUf="SP", idLegislatura=57)]


@pytest.mark.parametrize("document", ["12345678909", "12345678000190"])
def test_expense_import_discards_supplier_identifiers(engine, document):
    database, schema = engine
    import_deputies(database, DeputiesClient())
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Ano-2026.json", json.dumps({"dados": [{
            "idDocumento": "987", "numeroDeputadoID": 123,
            "ano": 2026, "mes": 10, "fornecedor": "Fornecedor de teste",
            "cnpjCPF": document, "email": "pessoal@example.invalid",
            "descricao": "Despesa de teste", "valorLiquido": "12,34",
        }]}))

    def respond(request):
        assert str(request.url) == "https://www.camara.leg.br/cotas/Ano-2026.json.zip"
        return httpx.Response(200, content=buffer.getvalue())

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        result = import_camara_expenses(database, year=2026, client=client)
        repeated = import_camara_expenses(database, year=2026, client=client)
    assert result["inserted"] == repeated["updated"] == 1
    assert repeated["inserted"] == 0
    with Session(database) as session:
        expense = session.scalar(select(ParliamentaryExpense))
        assert expense.external_id == "2026:987"
        assert expense.supplier_name == "Fornecedor de teste"
        assert expense.amount_net == Decimal("12.34")
        record = session.get(SourceRecord, expense.source_record_id)
        assert record.payload == {"year": 2026, "filename": "Ano-2026.json", "row_count": 1}
        assert record.normalizer_version == "ceap-v3"
        assert document not in json.dumps(record.payload)
        assert "pessoal@example.invalid" not in json.dumps(record.payload)
    columns = inspect(database).get_columns("parliamentary_expenses", schema=schema)
    assert "supplier_document" not in {column["name"] for column in columns}


def test_expense_document_link_must_belong_to_camara_https():
    official = "https://www.camara.leg.br/cota-parlamentar/documentos/publ/123.pdf"
    assert official_camara_document_url(official) == official
    assert official_camara_document_url("http://www.camara.leg.br/documento.pdf") is None
    assert official_camara_document_url("https://camara.leg.br.example/documento.pdf") is None


def test_expense_document_ids_are_namespaced_by_year(engine):
    database, _ = engine
    import_deputies(database, DeputiesClient())

    def respond(request):
        year = int(str(request.url).split("Ano-")[1].split(".")[0])
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(
                f"Ano-{year}.json",
                json.dumps(
                    {
                        "dados": [
                            {
                                "idDocumento": "987",
                                "numeroDeputadoID": 123,
                                "ano": year,
                                "mes": 1,
                                "descricao": "Despesa de teste",
                                "valorLiquido": "10,00",
                            }
                        ]
                    }
                ),
            )
        return httpx.Response(200, content=buffer.getvalue())

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        import_camara_expenses(database, year=2023, client=client)
        import_camara_expenses(database, year=2024, client=client)
    with Session(database) as session:
        identifiers = set(session.scalars(select(ParliamentaryExpense.external_id)))
    assert identifiers == {"2023:987", "2024:987"}


def ceap_archive(*rows):
    payload = json.dumps({"dados": rows}).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Ano-2026.json", payload)
    return buffer.getvalue(), hashlib.sha256(payload).hexdigest()


def test_expense_archive_enforces_expanded_limit(monkeypatch):
    monkeypatch.setattr("app.jobs.import_camara_expenses.MAX_EXPANDED_BYTES", 128)
    content, _ = ceap_archive({"descricao": "x" * 256})

    with pytest.raises(ExpenseSourceError, match="limite de tamanho"), open_expense_file(content):
        pytest.fail("O ZIP acima do limite foi aceito.")


@pytest.mark.parametrize("payload", [b'{"dados":[{}]}{}', b'{"dados":[{},1]}', b'{"dados":[]}'])
def test_expense_archive_rejects_malformed_expenses(payload):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Ano-2026.json", payload)

    with pytest.raises(ExpenseSourceError), open_expense_file(buffer.getvalue()) as (_, _, rows):
        list(rows)


def test_expense_provenance_distinguishes_correction_with_same_row_count(engine):
    database, _ = engine
    import_deputies(database, DeputiesClient())
    row = {"idDocumento": "987", "numeroDeputadoID": 123, "ano": 2026, "valorLiquido": "12,34"}
    original, original_digest = ceap_archive(row)
    corrected, corrected_digest = ceap_archive({**row, "valorLiquido": "45,67"})
    files = iter([original, corrected, corrected])
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=next(files)))

    with httpx.Client(transport=transport) as client:
        results = [import_camara_expenses(database, year=2026, client=client) for _ in range(3)]

    with Session(database) as session:
        records = session.scalars(select(SourceRecord).where(SourceRecord.entity == "ceap_file")).all()
        assert {record.payload_hash for record in records} == {original_digest, corrected_digest}
        expense = session.scalars(select(ParliamentaryExpense)).one()
        assert expense.amount_net == Decimal("45.67")
        current = session.get(SourceRecord, expense.source_record_id)
        assert current.payload_hash == corrected_digest
        assert str(current.last_run_id) == results[-1]["run_id"]


def test_expense_import_recovers_abandoned_run_and_rolls_back_wrong_year(engine, monkeypatch):
    monkeypatch.setattr("app.jobs.import_camara_expenses.BATCH_SIZE", 1)
    database, _ = engine
    import_deputies(database, DeputiesClient())
    row = {"idDocumento": "987", "numeroDeputadoID": 123, "ano": 2026, "valorLiquido": "12,34"}
    original, original_digest = ceap_archive(row)
    mixed, _ = ceap_archive(
        {**row, "valorLiquido": "45,67"},
        {**row, "idDocumento": "654", "ano": 2025},
    )
    files = iter([original, mixed])
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=next(files)))

    with httpx.Client(transport=transport) as client:
        import_camara_expenses(database, year=2026, client=client)
        with Session(database) as session, session.begin():
            previous = session.scalars(select(ImportRun).where(ImportRun.job == JOB)).one()
            session.add(ImportRun(job=JOB, status="running", started_at=previous.started_at))
        with pytest.raises(ExpenseImportFailed, match="exercício incompatível"):
            import_camara_expenses(database, year=2026, client=client)

    with Session(database) as session:
        runs = {
            run.status: run for run in session.scalars(select(ImportRun).where(ImportRun.job == JOB))
        }
        assert set(runs) == {"success", "interrupted", "failed"}
        assert runs["interrupted"].finished_at is not None
        assert runs["failed"].error_code == "source_error"
        expense = session.scalars(select(ParliamentaryExpense)).one()
        assert expense.amount_net == Decimal("12.34")
        records = session.scalars(select(SourceRecord).where(SourceRecord.entity == "ceap_file"))
        assert records.one().payload_hash == original_digest
