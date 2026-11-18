import os
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from app.db import models
from app.db.base import Base
from app.api.routes.legislation import get_voting, search_votings
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.proposicoes.models import Proposition
from app.modules.votacoes.models import Voting, VotingProposition
from app.services.voting_presentation import voting_presentations


def test_list_and_detail_share_headline_with_one_batch_query():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Execute scripts/test_backend.py para PostgreSQL isolado.")
    root = create_engine(url)
    schema = "test_" + uuid4().hex
    with root.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = root.execution_options(schema_translate_map={None: schema})
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db, db.begin():
            seen = datetime.now(timezone.utc)
            run = ImportRun(job="fixture", status="success", started_at=seen)
            db.add(run)
            db.flush()
            origin = SourceRecord(source="camara", entity="fixture", external_id="1",
                payload={}, payload_hash="fixture", normalizer_version="fixture",
                source_url="https://dadosabertos.camara.leg.br/", first_seen_at=seen,
                last_seen_at=seen, last_run_id=run.id)
            db.add(origin)
            db.flush()
            provenance = dict(source="camara", source_url=origin.source_url,
                              collected_at=seen, source_record_id=origin.id)
            prop = Proposition(external_id="2654356", kind="REL", number=1, year=2026,
                summary="Emendas ao Projeto de Lei Orçamentária Anual para 2027.", **provenance)
            db.add(prop)
            db.flush()
            rows = []
            for number in range(12):
                row = Voting(external_id=f"fixture-{number}", description="Aprovada",
                             approved=True, occurred_on=date(2026, 11, 18), **provenance)
                db.add(row)
                db.flush()
                db.add(VotingProposition(voting_id=row.id, proposition_id=prop.id,
                                        relation_type="object", **provenance))
                rows.append(row)
            db.flush()
            queries = []
            def track(conn, cursor, statement, parameters, context, executemany):
                queries.append(statement)
            event.listen(engine, "before_cursor_execute", track)
            try:
                contexts = voting_presentations(db, rows)
                assert len(queries) == 1
            finally:
                event.remove(engine, "before_cursor_execute", track)
            expected = "Aprovado relatório sobre emendas ao Orçamento de 2027"
            assert all(value["display_title"] == expected for value in contexts.values())
            detail = get_voting(rows[0].id, db=db)
            page = search_votings(source="camara", q=None, year=None, result=None,
                                 mode=None, order="newest", limit=12, offset=0, db=db)
            assert detail.display_title == expected
            assert all(item.display_title == expected for item in page.items)
            assert detail.description == "Aprovada"
            assert detail.propositions[0].relation_type == "object"
    finally:
        with root.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()
