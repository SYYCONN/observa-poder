import os
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.db import models
from app.db.base import Base
from app.jobs import import_camara_votes as job
from app.modules.parlamentares.models import Mandate, Parliamentarian
from app.modules.votacoes.models import Vote, Voting


@pytest.fixture
def engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Execute scripts/test_backend.py para PostgreSQL isolado.")
    root = create_engine(url)
    schema = "test_" + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = root.execution_options(schema_translate_map={None: schema})
    Base.metadata.create_all(scoped)
    try:
        yield scoped
    finally:
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def test_annual_votes_create_historical_parliamentarian_idempotently(engine):
    votings = (
        "id;data;dataHoraRegistro;descricao;ultimaApresentacaoProposicao_descricao;"
        "uriOrgao;aprovacao;uri\n"
        "vote-1;2025-03-10;2025-03-10T15:00:00;Votação nominal;;"
        ";1;https://dadosabertos.camara.leg.br/api/v2/votacoes/vote-1\n"
    ).encode()
    votes = (
        "idVotacao;uriVotacao;dataHoraVoto;voto;deputado_id;deputado_uri;"
        "deputado_nome;deputado_siglaPartido;deputado_uriPartido;deputado_siglaUf;"
        "deputado_idLegislatura;deputado_urlFoto\n"
        "vote-1;https://dadosabertos.camara.leg.br/api/v2/votacoes/vote-1;"
        "2025-03-10T15:01:00;Sim;999;"
        "https://dadosabertos.camara.leg.br/api/v2/deputados/999;Deputada Histórica;"
        "ABC;https://dadosabertos.camara.leg.br/api/v2/partidos/1;SP;57;"
        "https://www.camara.leg.br/foto/999.jpg\n"
    ).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        payload = votes if "votacoesVotos" in str(request.url) else votings
        return httpx.Response(200, content=payload, request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        first = job.import_camara_votes(engine, year=2025, client=client)
        second = job.import_camara_votes(engine, year=2025, client=client)

    assert first["parliamentarians_inserted"] == first["votes_inserted"] == 1
    assert second["parliamentarians_inserted"] == second["votes_inserted"] == 0
    with Session(engine) as session:
        person = session.scalar(select(Parliamentarian))
        mandate = session.scalar(select(Mandate))
        assert person.name == "Deputada Histórica"
        assert person.is_current is False
        assert mandate.parliamentarian_id == person.id
        assert mandate.party == "ABC"
        assert session.scalar(select(func.count()).select_from(Vote)) == 1
        assert session.scalar(select(Voting)).mode == "nominal"
