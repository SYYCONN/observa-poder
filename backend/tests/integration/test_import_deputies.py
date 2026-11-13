import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.db import models
from app.db.base import Base
from app.integrations.camara.client import SourceError
from app.integrations.camara.schemas import BASE_URL, Deputy
from app.jobs import import_deputies as job
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.parlamentares.models import Mandate, MandateObservation, Parliamentarian


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


def deputy(identifier=1, party="A", legislature=57):
    return Deputy(
        id=identifier,
        uri=f"{BASE_URL}/deputados/{identifier}",
        nome="Homônimo",
        siglaUf="SP",
        siglaPartido=party,
        uriPartido=f"{BASE_URL}/partidos/{party}",
        idLegislatura=legislature,
    )


class StubClient:
    def __init__(self, records=None, fail=False):
        self.records = records or [deputy()]
        self.fail = fail
        self.pages = 1
        self.received = len(self.records)

    def fetch_current_deputies(self):
        if self.fail:
            raise SourceError("Falha controlada na página seguinte.")
        return self.records

    def close(self):
        pass


def count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def test_second_import_is_idempotent(engine):
    first = job.import_deputies(engine, StubClient([deputy(1), deputy(2)]))
    second = job.import_deputies(engine, StubClient([deputy(1), deputy(2)]))
    assert first["inserted"] == 2
    assert second["inserted"] == second["updated"] == 0
    assert second["unchanged"] == 2
    with Session(engine) as s:
        assert count(s, Parliamentarian) == 2  # homônimos não se fundem
        assert count(s, Mandate) == count(s, MandateObservation) == count(s, SourceRecord) == 2
        assert count(s, ImportRun) == 2


def test_party_changes_preserve_observations_and_return_to_previous_party(engine):
    for party in ["A", "B", "A"]:
        job.import_deputies(engine, StubClient([deputy(party=party)]))
    with Session(engine) as s:
        assert count(s, Parliamentarian) == count(s, Mandate) == 1
        assert count(s, SourceRecord) == 2
        observations = s.scalars(
            select(MandateObservation).order_by(MandateObservation.observed_at)
        ).all()
        assert [o.party for o in observations] == ["A", "B", "A"]
        mandate = s.scalar(select(Mandate))
        assert mandate.party == "A"
        assert mandate.started_on is None and mandate.ended_on is None


def test_new_legislature_does_not_replace_previous_mandate(engine):
    job.import_deputies(engine, StubClient())
    job.import_deputies(engine, StubClient([deputy(legislature=58)]))
    with Session(engine) as s:
        assert count(s, Parliamentarian) == 1
        assert count(s, Mandate) == 2


def test_fetch_failure_leaves_data_unchanged_and_records_failure(engine):
    job.import_deputies(engine, StubClient())
    with pytest.raises(job.ImportFailed):
        job.import_deputies(engine, StubClient(fail=True))
    with Session(engine) as s:
        assert count(s, Parliamentarian) == count(s, SourceRecord) == 1
        run = s.scalar(select(ImportRun).where(ImportRun.status == "failed"))
        assert run.error_code == "source_error"
        assert run.inserted == 0


def test_transaction_rolls_back_partial_processing(engine, monkeypatch):
    original = job.persist_deputies

    def failing(session, records, run_id, observed_at):
        original(session, records, run_id, observed_at)
        session.flush()
        raise RuntimeError("private-password-must-not-be-logged")

    monkeypatch.setattr(job, "persist_deputies", failing)
    with pytest.raises(job.ImportFailed):
        job.import_deputies(engine, StubClient())
    with Session(engine) as s:
        assert count(s, Parliamentarian) == count(s, SourceRecord) == count(s, Mandate) == 0
        run = s.scalar(select(ImportRun))
        assert run.status == "failed"
        assert "private-password" not in run.error_message


def test_concurrent_job_is_rejected(engine):
    with engine.connect() as lock:
        lock.execute(text("SELECT pg_advisory_lock(:key)"), {"key": job.LOCK_KEY})
        lock.commit()
        try:
            with pytest.raises(job.ImportBusy):
                job.import_deputies(engine, StubClient())
        finally:
            lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": job.LOCK_KEY})
            lock.commit()


def test_abandoned_run_recovered_and_missing_person_not_deleted(engine):
    job.import_deputies(engine, StubClient([deputy(i) for i in range(1, 5)]))
    with Session(engine) as s, s.begin():
        s.add(ImportRun(job=job.JOB, status="running", started_at=datetime.now(timezone.utc)))
    job.import_deputies(engine, StubClient([deputy(i) for i in range(1, 4)]))
    with Session(engine) as s:
        assert count(s, Parliamentarian) == 4
        current = s.scalars(
            select(Parliamentarian).where(Parliamentarian.is_current.is_(True))
        ).all()
        historical = s.scalars(
            select(Parliamentarian).where(Parliamentarian.is_current.is_(False))
        ).all()
        assert len(current) == 3
        assert [person.external_id for person in historical] == ["4"]
        assert s.scalar(select(ImportRun).where(ImportRun.status == "interrupted")) is not None


def test_suspicious_drop_not_published(engine):
    job.import_deputies(engine, StubClient([deputy(1), deputy(2)]))
    with pytest.raises(job.ImportFailed):
        job.import_deputies(engine, StubClient())
    with Session(engine) as s:
        assert count(s, Parliamentarian) == 2
        assert s.scalar(select(ImportRun).where(ImportRun.status == "failed")) is not None
