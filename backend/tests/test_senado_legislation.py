from datetime import datetime, timezone

from app.jobs.import_senado_legislation import _as_list, parse_date


def test_senado_naive_dates_use_sao_paulo():
    assert parse_date("2026-11-03T10:00:00") == datetime(2026, 11, 3, 13, tzinfo=timezone.utc)


def test_senado_aware_dates_preserve_the_instant():
    assert parse_date("2026-11-03T10:00:00-04:00") == datetime(2026, 11, 3, 14, tzinfo=timezone.utc)
    assert parse_date(None) is None


def test_singleton_official_collections_are_not_lost():
    vote = {"CodigoParlamentar": "123", "Voto": "Sim"}
    assert _as_list(vote) == [vote]
    assert _as_list([vote]) == [vote]
    assert _as_list(None) == []
