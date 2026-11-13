from decimal import Decimal
from types import SimpleNamespace

from app.services.amendments_pdf import _complete_sum, _short_money
from app.services.staff_pdf import _total


def test_pdf_totals_keep_missing_values_unknown():
    rows = [
        SimpleNamespace(paid_amount=Decimal("10")),
        SimpleNamespace(paid_amount=None),
    ]
    assert _complete_sum(rows, "paid_amount") is None
    assert _short_money(None) == "Não informado"
    assert _total([Decimal("10"), None]) is None


def test_pdf_totals_sum_only_complete_series():
    rows = [
        SimpleNamespace(paid_amount=Decimal("10")),
        SimpleNamespace(paid_amount=Decimal("2")),
    ]
    assert _complete_sum(rows, "paid_amount") == Decimal("12")
    assert _total([Decimal("10"), Decimal("2")]) == Decimal("12")
