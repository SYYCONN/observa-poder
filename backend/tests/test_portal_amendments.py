from decimal import Decimal

from app.integrations.portal_transparencia.amendments import (
    amendments_query_url,
    parse_amendments,
    parse_amount,
)
from app.jobs.import_portal_amendments import _complete_sum


def test_parse_portal_amounts():
    assert parse_amount("R$ 1.234,56") == Decimal("1234.56")
    assert parse_amount("1234.56") == Decimal("1234.56")


def test_parse_amendments():
    result = parse_amendments(
        [
            {
                "codigoEmenda": "123456",
                "ano": 2026,
                "nomeAutor": "AJ Albuquerque",
                "valorEmpenhado": "1.234,56",
                "valorLiquidado": "1.000,00",
                "valorPago": "900,00",
            }
        ]
    )
    assert result[0]["committed"] == Decimal("1234.56")
    assert result[0]["paid"] == Decimal("900.00")


def test_amendments_query_url_has_author_and_year():
    url = amendments_query_url("AJ Albuquerque", 2026)
    assert "ano=2026" in url
    assert "nomeAutor=AJ+Albuquerque" in url


def test_api_summary_does_not_turn_missing_amount_into_zero():
    assert _complete_sum([Decimal("10"), None]) is None
    assert _complete_sum([Decimal("10"), Decimal("2")]) == Decimal("12")
