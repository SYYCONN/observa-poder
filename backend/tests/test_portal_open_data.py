import io
import zipfile
from decimal import Decimal

from app.integrations.portal_transparencia.open_data import (
    group_open_data_amendments,
    normalize_author_name,
)
from app.jobs.import_portal_amendments_open_data import _sum, _unique_people_by_name


def _archive(csv_text: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("EmendasParlamentares.csv", csv_text.encode("cp1252"))
    return buffer.getvalue()


def test_normalize_author_name_removes_accents_and_punctuation():
    assert normalize_author_name("Márcio de Souza") == "MARCIO DE SOUZA"


def test_group_open_data_amendments_reads_only_selected_year():
    header = (
        '"Código da Emenda";"Ano da Emenda";"Nome do Autor da Emenda";'
        '"Valor Empenhado";"Valor Liquidado";"Valor Pago"\n'
    )
    rows = (
        '"202639020001";"2026";"AJ ALBUQUERQUE";"1.234,50";"900,00";"800,00"\n'
        '"202539020001";"2025";"AJ ALBUQUERQUE";"2.000,00";"0,00";"0,00"\n'
    )
    grouped = group_open_data_amendments(_archive(header + rows), 2026)

    assert list(grouped) == ["AJ ALBUQUERQUE"]
    record = grouped["AJ ALBUQUERQUE"]["202639020001"]
    assert record.committed == Decimal("1234.50")
    assert record.liquidated == Decimal("900")
    assert record.paid == Decimal("800")


def test_amendment_match_excludes_homonyms_and_incomplete_totals():
    people = [("id-1", "Márcio Souza"), ("id-2", "MARCIO SOUZA"), ("id-3", "Ana Lima")]
    assert _unique_people_by_name(people) == {"ANA LIMA": "id-3"}
    assert _sum([Decimal("10"), None]) is None
    assert _sum([Decimal("10"), Decimal("2")]) == Decimal("12")
