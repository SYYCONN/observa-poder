from datetime import datetime, timezone

import pytest
import httpx

from app.integrations.legislation import camara_boolean, legislative_datetime, vote_position
from app.jobs.import_camara_votes import parse_datetime
from app.jobs.import_legislation import dt
from app.jobs.import_legislation import get_json
from app.jobs.import_senado_legislation import parse_date


@pytest.mark.parametrize("parse", [legislative_datetime, parse_datetime, dt, parse_date])
def test_legislative_dates_use_business_timezone_and_keep_explicit_offsets(parse):
    local = parse("2026-11-03T00:30:00")
    assert local.astimezone(timezone.utc) == datetime(2026, 11, 3, 3, 30, tzinfo=timezone.utc)
    assert parse("2026-11-03T00:30:00Z") == datetime(2026, 11, 3, 0, 30, tzinfo=timezone.utc)
    assert parse("2026-11-03T00:30:00+02:00") == datetime(2026, 11, 2, 22, 30, tzinfo=timezone.utc)
    assert parse("2026-11-03").date().isoformat() == "2026-11-03"
    assert parse(None) is None
    assert parse("") is None


@pytest.mark.parametrize(
    "raw,expected",
    [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        ("1", True),
        ("0", False),
        (None, None),
        ("", None),
        ("desconhecido", None),
        (2, None),
        ([], None),
    ],
)
def test_camara_boolean_does_not_infer_unknown_values(raw, expected):
    assert camara_boolean(raw) is expected


def test_missing_position_does_not_create_a_vote():
    assert vote_position(None, "", "  ") is None
    assert vote_position(" ", " Sim ") == "Sim"
    assert vote_position("Abstenção", "Sim") == "Abstenção"


def test_camara_json_retries_a_transient_connection_failure(monkeypatch):
    attempts = 0

    def respond(request):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectTimeout("fonte temporariamente indisponível", request=request)
        return httpx.Response(200, json={"dados": [{"id": 1}]})

    monkeypatch.setattr("app.jobs.import_legislation.time.sleep", lambda _: None)
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        assert get_json(client, "https://example.test")["dados"] == [{"id": 1}]
    assert attempts == 2
