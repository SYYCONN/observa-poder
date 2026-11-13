import os
import json
from datetime import date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.db import models
from app.db.base import Base
from app.integrations.camara.schemas import BASE_URL, Deputy, DeputyProfile, DeputyStatus
from app.jobs.import_camara_deputy_profiles import (
    exercise_period,
    import_camara_deputy_profiles,
    is_individual_history_source,
    parse_firecrawl_history,
)
from app.jobs.import_deputies import import_deputies
from app.modules.parlamentares.models import Mandate, Parliamentarian


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


class RosterClient:
    pages = 1
    received = 1

    def fetch_current_deputies(self):
        return [
            Deputy(
                id=220705,
                uri=f"{BASE_URL}/deputados/220705",
                nome="Deltan Dallagnol",
                siglaPartido="PODE",
                uriPartido=f"{BASE_URL}/partidos/36896",
                siglaUf="PR",
                idLegislatura=57,
                urlFoto=None,
            )
        ]

    def close(self):
        pass


class ProfileClient:
    sleep = staticmethod(lambda _: None)

    def fetch_deputy_profile(self, identifier):
        assert identifier == 220705
        return (
            DeputyProfile(
                id=identifier,
                nomeCivil="DELTAN MARTINAZZO DALLAGNOL",
                dataNascimento=date(1980, 1, 15),
            ),
            [
                DeputyStatus(
                    id=identifier,
                    idLegislatura=57,
                    dataHora=datetime.fromisoformat("2023-02-01T12:05:00"),
                    situacao="Exercício",
                    descricaoStatus="Entrada - Posse de Eleito Titular",
                ),
                DeputyStatus(
                    id=identifier,
                    idLegislatura=57,
                    dataHora=datetime.fromisoformat("2023-06-06T16:54:00"),
                    situacao="VACANCIA",
                    descricaoStatus="Saída - Afastamento definitivo - Perda de Mandato",
                ),
            ],
        )

    def close(self):
        pass


def test_profile_import_is_idempotent_and_preserves_official_dates(engine):
    import_deputies(engine, RosterClient())
    first = import_camara_deputy_profiles(engine, ProfileClient())
    second = import_camara_deputy_profiles(engine, ProfileClient())
    assert first["inserted"] == 1
    assert second["unchanged"] == 1
    with Session(engine) as session:
        person = session.scalar(select(Parliamentarian))
        mandate = session.scalar(select(Mandate))
        assert person.birth_date == date(1980, 1, 15)
        assert person.profile_source_record_id is not None
        assert mandate.started_on == date(2023, 2, 1)
        assert mandate.ended_on == date(2023, 6, 6)
        assert mandate.source_url.endswith("/220705/historico")


def test_period_ignores_unlabelled_status_and_temporary_exit_followed_by_entry():
    statuses = [
        DeputyStatus(
            id=1,
            idLegislatura=57,
            dataHora=datetime.fromisoformat("2023-01-01T00:00:00"),
            situacao=None,
            descricaoStatus="Nome no início da legislatura",
        ),
        DeputyStatus(
            id=1,
            idLegislatura=57,
            dataHora=datetime.fromisoformat("2023-02-01T00:00:00"),
            situacao="Exercício",
            descricaoStatus="Entrada - Posse",
        ),
        DeputyStatus(
            id=1,
            idLegislatura=57,
            dataHora=datetime.fromisoformat("2024-01-01T00:00:00"),
            situacao="Licença",
            descricaoStatus="Saída - Licença",
        ),
        DeputyStatus(
            id=1,
            idLegislatura=57,
            dataHora=datetime.fromisoformat("2024-02-01T00:00:00"),
            situacao="Exercício",
            descricaoStatus="Entrada - Retorno de licença",
        ),
    ]
    assert exercise_period(statuses, "57") == (date(2023, 2, 1), None)


def test_firecrawl_history_parser_accepts_only_matching_official_identifier(tmp_path):
    path = tmp_path / "dadosabertos.camara.leg.br-api-v2-deputados-220705-historico.md"
    path.write_text(
        json.dumps(
            {
                "rawHtml": (
                    "<xml><dados><statusParlamentar><id>220705</id>"
                    "<idLegislatura>57</idLegislatura>"
                    "<dataHora>2023-02-01T12:05</dataHora>"
                    "<situacao>Exercício</situacao>"
                    "<descricaoStatus>Entrada - Posse</descricaoStatus>"
                    "</statusParlamentar></dados></xml>"
                )
            }
        ),
        encoding="utf-8",
    )
    identifier, statuses = parse_firecrawl_history(path)
    assert identifier == "220705"
    assert statuses[0].idLegislatura == 57
    assert statuses[0].dataHora.date() == date(2023, 2, 1)


def test_individual_history_source_is_distinguished_from_bulk_file():
    assert is_individual_history_source(f"{BASE_URL}/deputados/220705/historico")
    assert not is_individual_history_source(
        "https://dadosabertos.camara.leg.br/arquivos/deputadosHistorico/json/"
        "deputadosHistorico.json"
    )
