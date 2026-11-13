"""Importa despesas da Cota Parlamentar publicada pela Câmara."""

import argparse
import hashlib
import io
import json
import zipfile
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from itertools import batched
from urllib.parse import urlparse
from uuid import uuid4

import httpx
import ijson

from app.integrations.download import download_bytes
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.core.dates import local_today
from app.db.session import get_engine
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.financas.models import ParliamentaryExpense
from app.modules.parlamentares.models import Parliamentarian
from app.modules.proposicoes.linking import normalize_name

JOB = "camara.parliamentary_expenses"
SOURCE = "camara"
LOCK_KEY = 2810202606
NORMALIZER_VERSION = "ceap-v3"
SOURCE_TEMPLATE = "https://www.camara.leg.br/cotas/Ano-{year}.json.zip"
MAX_EXPANDED_BYTES = 256 * 1024**2
BATCH_SIZE = 1000


class ExpenseSourceError(Exception):
    """Falha da fonte com mensagem própria para logs e auditoria."""


class ExpenseImportFailed(RuntimeError):
    pass


def now() -> datetime:
    return datetime.now(timezone.utc)


def parse_decimal(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        text_value = str(value).strip()
        if "," in text_value:
            text_value = text_value.replace(".", "").replace(",", ".")
        return Decimal(text_value)
    except (InvalidOperation, ValueError):
        return None


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def official_camara_document_url(value) -> str | None:
    """Publica somente links HTTPS pertencentes ao domínio oficial da Câmara."""

    if not value:
        return None
    candidate = str(value).strip()
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (host == "camara.leg.br" or host.endswith(".camara.leg.br")):
        return None
    return candidate


@contextmanager
def open_expense_file(content: bytes):
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            files = [
                entry for entry in archive.infolist()
                if not entry.is_dir() and entry.filename.lower().endswith(".json")
            ]
            if len(files) != 1:
                raise ExpenseSourceError("O arquivo CEAP deve conter um único JSON.")
            filename = files[0].filename
            if files[0].file_size > MAX_EXPANDED_BYTES:
                raise ExpenseSourceError("JSON anual da CEAP excedeu o limite de tamanho.")
            with archive.open(files[0]) as entry:
                digest = hashlib.sha256()
                expanded_bytes = 0
                while chunk := entry.read(65536):
                    expanded_bytes += len(chunk)
                    if expanded_bytes > MAX_EXPANDED_BYTES:
                        raise ExpenseSourceError("JSON anual da CEAP excedeu o limite de tamanho.")
                    digest.update(chunk)
                entry.seek(0)
                yield filename, digest.hexdigest(), expense_rows(entry)
    except (zipfile.BadZipFile, UnicodeError, ijson.JSONError):
        raise ExpenseSourceError("O arquivo CEAP não contém um ZIP com JSON válido.") from None


def expense_rows(entry):
    invalid_rows = "O arquivo CEAP não contém uma lista válida de despesas."
    events = ijson.parse(entry)
    if next(events, None) != ("", "start_map", None):
        raise ExpenseSourceError(invalid_rows)

    def array_events():
        found = False
        for prefix, event, value in events:
            if (prefix, event, value) == ("", "map_key", "dados"):
                if found or next(events, None) != ("dados", "start_array", None):
                    raise ExpenseSourceError(invalid_rows)
                found = True
                for item_event in events:
                    if item_event == ("dados", "end_array", None):
                        break
                    yield item_event

    found_row = False
    for row in ijson.items(array_events(), "dados.item"):
        if not isinstance(row, dict):
            raise ExpenseSourceError(invalid_rows)
        found_row = True
        yield row
    if not found_row:
        raise ExpenseSourceError(invalid_rows)


def source_file_record(session: Session, run_id, year: int, payload: dict, digest: str, seen: datetime):
    url = SOURCE_TEMPLATE.format(year=year)
    row = session.scalar(
        select(SourceRecord).where(
            SourceRecord.source == SOURCE,
            SourceRecord.entity == "ceap_file",
            SourceRecord.external_id == str(year),
            SourceRecord.payload_hash == digest,
            SourceRecord.normalizer_version == NORMALIZER_VERSION,
        )
    )
    if row is None:
        row = SourceRecord(
            source=SOURCE,
            entity="ceap_file",
            external_id=str(year),
            source_url=url,
            payload_hash=digest,
            normalizer_version=NORMALIZER_VERSION,
            payload=payload,
            first_seen_at=seen,
            last_seen_at=seen,
            last_run_id=run_id,
        )
        session.add(row)
        session.flush()
    else:
        row.last_seen_at = seen
        row.last_run_id = run_id
    return row, url


def import_camara_expenses(engine, year: int | None = None, client=None):
    year = year or local_today().year
    owns_client = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(120, connect=15), follow_redirects=True)
    run_id = uuid4()
    started = now()
    try:
        with engine.connect() as lock:
            if not lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}):
                raise RuntimeError("Já existe uma importação financeira em execução.")
            lock.commit()
            try:
                with Session(engine) as session, session.begin():
                    session.execute(
                        update(ImportRun)
                        .where(ImportRun.job == JOB, ImportRun.status == "running")
                        .values(
                            status="interrupted",
                            finished_at=started,
                            error_code="interrupted",
                            error_message="Execução anterior interrompida. A coleta foi reiniciada.",
                        )
                    )
                    session.add(
                        ImportRun(
                            id=run_id,
                            job=JOB,
                            status="running",
                            started_at=started,
                        )
                    )

                url = SOURCE_TEMPLATE.format(year=year)
                try:
                    content = download_bytes(client, url, max_bytes=48 * 1024**2)
                except (httpx.HTTPError, ValueError):
                    raise ExpenseSourceError("Falha ao baixar o arquivo anual da CEAP.") from None
                seen = now()
                with open_expense_file(content) as (filename, digest, rows), Session(engine) as session:
                    parliamentarian_rows = session.execute(
                        select(Parliamentarian.external_id, Parliamentarian.name, Parliamentarian.id)
                        .where(Parliamentarian.source == SOURCE)
                    ).all()
                    parliamentarians = {external_id: person_id for external_id, _, person_id in parliamentarian_rows}
                    names = {}
                    for _, name, person_id in parliamentarian_rows:
                        key = normalize_name(name)
                        if key in names:
                            names[key] = None
                        else:
                            names[key] = person_id
                    source_record, source_url = source_file_record(
                        session,
                        run_id,
                        year,
                        {"year": year, "filename": filename},
                        digest,
                        seen,
                    )
                    received = inserted = updated = skipped = 0
                    for batch in batched(rows, BATCH_SIZE):
                        received += len(batch)
                        entries = []
                        for item in batch:
                            document_id = str(item.get("idDocumento") or "").strip()
                            external_id = f"{year}:{document_id}" if document_id else ""
                            entries.append((external_id, item))
                        existing = {
                            row.external_id: row
                            for row in session.scalars(
                                select(ParliamentaryExpense).where(
                                    ParliamentaryExpense.source == SOURCE,
                                    ParliamentaryExpense.external_id.in_(
                                        {external_id for external_id, _ in entries if external_id}
                                    ),
                                )
                            )
                        }
                        for external_id, item in entries:
                            item_year = item.get("ano")
                            if item_year not in (None, "") and str(item_year).strip() != str(year):
                                raise ExpenseSourceError("O arquivo CEAP contém um exercício incompatível.")
                            person_id = parliamentarians.get(str(item.get("numeroDeputadoID") or ""))
                            if person_id is None:
                                person_id = names.get(normalize_name(item.get("nomeParlamentar")))
                            if not external_id or person_id is None:
                                skipped += 1
                                continue
                            expense = existing.get(external_id)
                            if expense is None:
                                expense = ParliamentaryExpense(
                                    external_id=external_id,
                                    source=SOURCE,
                                )
                                session.add(expense)
                                existing[external_id] = expense
                                inserted += 1
                            else:
                                updated += 1
                            expense.parliamentarian_id = person_id
                            expense.occurred_on = parse_date(item.get("dataEmissao"))
                            expense.year = year
                            expense.month = item.get("mes")
                            expense.category = item.get("descricao") or "Categoria não informada"
                            expense.category_detail = item.get("descricaoEspecificacao") or None
                            expense.supplier_name = item.get("fornecedor") or None
                            expense.document_number = item.get("numero") or None
                            expense.document_type = item.get("tipoDocumento") or None
                            expense.amount_document = parse_decimal(item.get("valorDocumento"))
                            expense.amount_glossed = parse_decimal(item.get("valorGlosa"))
                            expense.amount_net = parse_decimal(item.get("valorLiquido"))
                            expense.reimbursement = item.get("ressarcimento") or None
                            expense.source_document_url = official_camara_document_url(
                                item.get("urlDocumento")
                            )
                            expense.source_url = source_url
                            expense.collected_at = seen
                            expense.source_record_id = source_record.id
                        session.flush()
                    source_record.payload = {**source_record.payload, "row_count": received}
                    run = session.get(ImportRun, run_id)
                    run.status = "success"
                    run.finished_at = now()
                    run.received = received
                    run.inserted = inserted
                    run.updated = updated
                    run.unchanged = max(received - skipped - inserted - updated, 0)
                    run.pages = 1
                    session.commit()
                return {
                    "run_id": str(run_id),
                    "status": "success",
                    "year": year,
                    "received": received,
                    "inserted": inserted,
                    "updated": updated,
                    "skipped": skipped,
                }
            except Exception as exc:
                if isinstance(exc, ExpenseSourceError):
                    code, message = "source_error", str(exc)
                else:
                    code = "processing_error"
                    message = "Erro interno ao importar despesas CEAP. A publicação foi revertida."
                with Session(engine) as session, session.begin():
                    run = session.get(ImportRun, run_id)
                    if run:
                        run.status = "failed"
                        run.finished_at = now()
                        run.error_code = code
                        run.error_message = message
                raise ExpenseImportFailed(f"Importação {run_id} falhou ({code}). {message}") from None
            finally:
                lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY})
                lock.commit()
    finally:
        if owns_client:
            client.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=None)
    args = parser.parse_args()
    print(json.dumps(import_camara_expenses(get_engine(), year=args.year), ensure_ascii=False))


if __name__ == "__main__":
    main()
