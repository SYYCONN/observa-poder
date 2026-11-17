import os
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.db import models
from app.db.base import Base
from app.jobs.import_camara_remuneration import import_camara_remuneration
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.financas.models import ParliamentaryRemuneration
from app.modules.parlamentares.models import Parliamentarian


@pytest.mark.parametrize("month, published", [(10, True), (11, False)])
def test_import_remuneration_keeps_available_details_when_one_returns_404(month, published):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Execute scripts/test_backend.py para PostgreSQL isolado.")
    root = create_engine(url)
    schema = "test_" + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = root.execution_options(schema_translate_map={None: schema})
    try:
        Base.metadata.create_all(engine)
        seen = datetime.now(timezone.utc)
        source_url = "https://www.camara.leg.br/"
        details = [("Pessoa Um", "sem-ficha"), ("Pessoa Dois", "com-ficha")]
        with Session(engine) as session, session.begin():
            run = ImportRun(job="teste", status="success", started_at=seen, finished_at=seen)
            session.add(run)
            session.flush()
            source = SourceRecord(
                source="camara", entity="deputado", external_id="teste", source_url=source_url,
                payload_hash="teste", normalizer_version="teste", payload={},
                first_seen_at=seen, last_seen_at=seen, last_run_id=run.id,
            )
            session.add(source)
            session.flush()
            for name, external_id in details:
                session.add(Parliamentarian(
                    source="camara", external_id=external_id, name=name, source_url=source_url,
                    collected_at=seen, source_record_id=source.id,
                ))

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/funcionarios"):
                rows = "".join(
                    f'<tr class="tabela-responsiva__linha"><td data-th="Nome"><a>{name}</a></td>'
                    f'<td><a href="{source_url}transparencia/recursos-humanos/remuneracao/{key}">'
                    f'Consulta</a></td></tr>'
                    for name, key in details
                )
                return httpx.Response(200, text=rows)
            if request.url.path.endswith("/sem-ficha"):
                return httpx.Response(404)
            return httpx.Response(200, text="10 2026 - FOLHA NORMAL <td>a - Remuneração Fixa</td><td>46.366,19</td>")

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            if not published:
                with pytest.raises(RuntimeError, match="competência"):
                    import_camara_remuneration(engine, 2026, month, client=client)
                with Session(engine) as session:
                    assert session.scalars(select(ParliamentaryRemuneration)).all() == []
                    assert session.scalars(select(ImportRun).where(ImportRun.job == "camara.parliamentary_remuneration")).one().status == "failed"
                return
            result = import_camara_remuneration(engine, 2026, month, client=client)
        assert result["status"] == "success"
        assert result["inserted"] == result["skipped"] == result["missing_details"] == 1
        with Session(engine) as session:
            row = session.scalars(select(ParliamentaryRemuneration)).one()
            assert row.fixed_amount == Decimal("46366.19")
            assert session.get(Parliamentarian, row.parliamentarian_id).external_id == "com-ficha"
    finally:
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()
