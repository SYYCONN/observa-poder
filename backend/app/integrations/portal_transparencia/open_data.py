"""Leitura dos arquivos abertos de emendas do Portal da Transparência."""

import csv
import io
import unicodedata
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterator

from app.integrations.portal_transparencia.amendments import parse_amount

PORTAL_AMENDMENTS_SOURCE_URL = "https://portaldatransparencia.gov.br/emendas/consulta"
PORTAL_AMENDMENTS_OPEN_DATA_URL = (
    "https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares"
)
PORTAL_AMENDMENTS_ARCHIVE_URL = (
    "https://dadosabertos-download.cgu.gov.br/PortalDaTransparencia/saida/"
    "emendas-parlamentares/EmendasParlamentares.zip"
)


@dataclass(frozen=True)
class OpenDataAmendment:
    code: str
    author: str
    year: int
    amendment_type: str | None
    locality: str | None
    municipality: str | None
    state: str | None
    function_name: str | None
    subfunction_name: str | None
    program_name: str | None
    action_name: str | None
    plan_name: str | None
    committed: Decimal | None
    liquidated: Decimal | None
    paid: Decimal | None


def normalize_author_name(value: str | None) -> str:
    """Normaliza nomes para o cruzamento entre bases públicas."""

    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    clean = "".join(
        char for char in without_accents.upper() if char.isalnum() or char == " "
    )
    return " ".join(clean.split())


def _csv_name(archive: zipfile.ZipFile) -> str:
    for name in archive.namelist():
        if name.rsplit("/", 1)[-1].lower() == "emendasparlamentares.csv":
            return name
    raise ValueError("O ZIP oficial não contém EmendasParlamentares.csv.")


def iter_open_data_amendments(content: bytes, year: int) -> Iterator[OpenDataAmendment]:
    """Percorre o CSV principal do ZIP oficial sem carregar todas as linhas."""

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entry = archive.getinfo(_csv_name(archive))
        if entry.file_size > 256 * 1024**2:
            raise ValueError("CSV de emendas excedeu o limite de tamanho.")
        with archive.open(entry) as raw_file:
            text_file = io.TextIOWrapper(raw_file, encoding="cp1252", errors="replace", newline="")
            reader = csv.DictReader(text_file, delimiter=";")
            for row in reader:
                if row.get("Ano da Emenda") != str(year):
                    continue
                code = (row.get("Código da Emenda") or "").strip()
                author = (row.get("Nome do Autor da Emenda") or "").strip()
                if not code or not author or normalize_author_name(author) in {
                    "SEM INFORMACAO",
                    "RELATOR GERAL",
                }:
                    continue
                state = (row.get("UF") or "").strip()
                yield OpenDataAmendment(
                    code=code,
                    author=author,
                    year=year,
                    amendment_type=row.get("Tipo de Emenda") or None,
                    locality=row.get("Localidade de aplicação do recurso") or None,
                    municipality=row.get("Município") or None,
                    state=state if len(state) == 2 else None,
                    function_name=row.get("Nome Função") or None,
                    subfunction_name=row.get("Nome Subfunção") or None,
                    program_name=row.get("Nome Programa") or None,
                    action_name=row.get("Nome Ação") or None,
                    plan_name=row.get("Nome Plano Orçamentário") or None,
                    committed=parse_amount(row.get("Valor Empenhado")),
                    liquidated=parse_amount(row.get("Valor Liquidado")),
                    paid=parse_amount(row.get("Valor Pago")),
                )


def group_open_data_amendments(
    content: bytes, year: int
) -> dict[str, dict[str, OpenDataAmendment]]:
    """Agrupa as emendas pelo nome normalizado do autor e pelo código oficial."""

    grouped: dict[str, dict[str, OpenDataAmendment]] = defaultdict(dict)
    for amendment in iter_open_data_amendments(content, year):
        grouped[normalize_author_name(amendment.author)][amendment.code] = amendment
    return dict(grouped)
