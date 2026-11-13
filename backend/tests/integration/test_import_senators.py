import os
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.db import models
from app.db.base import Base
from app.integrations.senado.client import Senator
from app.jobs.import_senators import import_senators
from app.modules.parlamentares.models import Mandate, Parliamentarian


@pytest.fixture
def engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Execute scripts/test_backend.py para PostgreSQL isolado.")
    root = create_engine(url)
    schema = "test_" + uuid4().hex
    with root.begin() as c:
        c.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = root.execution_options(schema_translate_map={None: schema})
    Base.metadata.create_all(scoped)
    try:
        yield scoped
    finally:
        with root.begin() as c:
            c.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


class StubClient:
    received = 1

    def fetch_current_senators(self):
        return [
            Senator(
                external_id="123",
                name="Senadora Exemplo",
                photo_url=None,
                source_url="https://senado.leg.br/perfil/123",
                state="SP",
                party="ABC",
                legislature="57",
                legislature_start=date(2023, 2, 1),
                legislature_end=date(2027, 1, 31),
            )
        ]

    def close(self):
        pass


def test_senator_import_does_not_infer_individual_mandate_dates(engine):
    first = import_senators(engine, StubClient())
    second = import_senators(engine, StubClient())
    assert first["inserted"] == 1
    assert second["unchanged"] == 1
    with Session(engine) as session, session.begin():
        assert session.scalar(select(func.count()).select_from(Parliamentarian)) == 1
        mandate = session.scalar(select(Mandate))
        assert mandate.started_on is None and mandate.ended_on is None
        # Simula os limites de legislatura gravados pela versão anterior.
        mandate.started_on = date(2023, 2, 1)
        mandate.ended_on = date(2027, 1, 31)
    repaired = import_senators(engine, StubClient())
    assert repaired["updated"] == 1
    with Session(engine) as session:
        mandate = session.scalar(select(Mandate))
        assert mandate.started_on is None and mandate.ended_on is None


def test_snapshot_preserves_history_and_restores_returning_senators(engine):
    from dataclasses import replace

    from app.api.routes.parliamentarians import list_parliamentarians
    from app.jobs.import_senators import ImportFailed

    client = StubClient()
    original = client.fetch_current_senators()[0]
    senators = [replace(original, external_id=str(code)) for code in range(1, 5)]
    client.fetch_current_senators = lambda: senators
    import_senators(engine, client)
    senators.pop()
    import_senators(engine, client)
    senators.pop()
    with pytest.raises(ImportFailed):
        import_senators(engine, client)

    with Session(engine) as session:
        for status, expected in (("current", {"1", "2", "3"}), ("historical", {"4"})):
            page = list_parliamentarians(
                search=None,
                state="SP",
                party="ABC",
                source="senado",
                status=status,
                limit=10,
                offset=0,
                db=session,
            )
            assert {item.external_id for item in page.items} == expected
            assert page.total == len(expected)
        person_id = page.items[0].id
        assert (
            session.scalar(
                select(func.count())
                .select_from(Mandate)
                .where(Mandate.parliamentarian_id == person_id)
            )
            == 1
        )

    senators.extend(replace(original, external_id=str(code)) for code in (3, 4))
    assert import_senators(engine, client)["updated"] == 1
    with Session(engine) as session:
        assert session.get(Parliamentarian, person_id).is_current is True
