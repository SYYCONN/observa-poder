"""Regressões legislativas com fontes simuladas e PostgreSQL isolado."""

import os
from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.db import models  # noqa: F401 — registra o metadata completo
from app.db.base import Base
from app.jobs import import_legislation as camara
from app.jobs import import_senado_legislation as senado
from app.modules.coletas.models import ImportRun, SourceRecord
from app.modules.parlamentares.models import Parliamentarian
from app.modules.votacoes.models import Vote, Voting, VotingProposition


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


def seed_people(engine, source):
    seen = datetime.now(timezone.utc)
    with Session(engine) as session, session.begin():
        run = ImportRun(job="fixture", status="success", started_at=seen)
        session.add(run)
        session.flush()
        record = SourceRecord(
            source=source,
            entity="fixture",
            external_id="fixture",
            source_url="https://example.test",
            payload_hash="a" * 64,
            normalizer_version="test",
            payload={},
            first_seen_at=seen,
            last_seen_at=seen,
            last_run_id=run.id,
        )
        session.add(record)
        session.flush()
        for identifier in (1, 2):
            session.add(
                Parliamentarian(
                    source=source,
                    external_id=str(identifier),
                    name=f"Pessoa {identifier}",
                    source_url=record.source_url,
                    collected_at=seen,
                    source_record_id=record.id,
                )
            )


@pytest.mark.parametrize("source", ["camara", "senado"])
@pytest.mark.parametrize(
    "result,expected", [("known_yes", True), ("known_no", False), ("unknown", None)]
)
def test_reimport_preserves_only_explicit_votes_and_results(engine, source, result, expected):
    seed_people(engine, source)
    camara_result = {"known_yes": "1", "known_no": "0", "unknown": "novo_codigo"}[result]
    senado_result = {"known_yes": "A", "known_no": "R", "unknown": "novo_codigo"}[result]

    def respond(request):
        path = request.url.path
        if source == "camara":
            if path.endswith("/proposicoes"):
                payload = []
            elif path.endswith("/votos"):
                payload = [
                    {"deputado_": {"id": 1}, "voto": " Sim "},
                    {"deputado_": {"id": 2}, "voto": " "},
                ]
            elif path.endswith("/votacoes"):
                payload = [{"id": "1", "descricao": "Teste", "aprovacao": camara_result}]
            else:
                payload = {}
            return httpx.Response(200, json={"dados": payload})
        if path.endswith("/processo"):
            return httpx.Response(200, json=[])
        return httpx.Response(
            200,
            json={
                "ListaVotacoes": {
                    "Votacoes": {
                        "Votacao": {
                            "CodigoVotacaoSve": "1",
                            "Resultado": senado_result,
                            "Votos": {
                                "VotoParlamentar": [
                                    {"CodigoParlamentar": "1", "Voto": " Sim "},
                                    {"CodigoParlamentar": "2", "Voto": " "},
                                ]
                            },
                        }
                    }
                }
            },
        )

    job = camara.import_legislation if source == "camara" else senado.import_senado_legislation
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        job(engine, client=client)
        job(engine, client=client)
    with Session(engine) as session:
        votings = session.scalars(select(Voting)).all()
        votes = session.scalars(select(Vote)).all()
        assert len(votings) == len(votes) == 1
        assert votings[0].approved is expected
        assert votes[0].position == "Sim"
        assert votes[0].source == source
        assert session.get(SourceRecord, votes[0].source_record_id) is not None


def test_senado_accepts_a_single_nominal_vote(engine):
    from app.api.routes.legislation import get_voting
    from app.api.routes.parliamentarians import get_parliamentarian, list_parliamentarian_votes

    seed_people(engine, "senado")

    def respond(request):
        if request.url.path.endswith("/processo"):
            return httpx.Response(200, json=[])
        return httpx.Response(
            200,
            json={
                "ListaVotacoes": {
                    "Votacoes": {
                        "Votacao": {
                            "CodigoVotacaoSve": "1",
                            "Votos": {
                                "VotoParlamentar": {"CodigoParlamentar": "1", "Voto": "Não"},
                            },
                        }
                    }
                }
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        senado.import_senado_legislation(engine, client=client)
    with Session(engine) as session:
        vote = session.scalar(select(Vote))
        voting = session.scalar(select(Voting))
        assert vote.position == "Não"
        assert voting.approved is None
        other = session.scalar(select(Parliamentarian).where(Parliamentarian.external_id == "2"))
        session.add(
            Vote(
                voting_id=voting.id,
                parliamentarian_id=other.id,
                source="senado",
                source_record_id=vote.source_record_id,
                source_url=vote.source_url,
                collected_at=vote.collected_at,
                position="registrado",
            )
        )
        assert [item.position for item in get_voting(voting.id, db=session).votes] == ["Não"]
        assert list_parliamentarian_votes(other.id, limit=8, offset=0, db=session).total == 0
        assert get_parliamentarian(other.id, db=session).votes_total == 0


def test_camara_uses_proposition_detail_and_explicit_author_flags(engine):
    from app.api.routes.legislation import get_proposition
    from app.jobs.generate_citizen_explanations import _process_one
    from app.modules.proposicoes.models import (
        Authorship,
        CitizenExplanationRun,
        Proposition,
        PropositionCitizenExplanation,
    )
    from app.services.citizen_drafts import AssistedDraftResult, VerificationResult

    def respond(request):
        path = request.url.path
        payloads = {
            "/api/v2/proposicoes": [{"id": 123, "siglaTipo": "PL", "ementa": "Resumo da lista"}],
            "/api/v2/proposicoes/123": {
                "id": 123,
                "siglaTipo": "PL",
                "numero": 1,
                "ano": 2026,
                "ementa": "Ementa detalhada",
                "ementaDetalhada": "Descrição oficial mais completa.",
                "urlInteiroTeor": "https://www.camara.leg.br/inteiro-teor/123",
                "keywords": "educação; transparência",
                "statusProposicao": {
                    "descricaoSituacao": "Aguardando despacho",
                    "siglaOrgao": "MESA",
                    "dataHora": "2026-11-04T10:00:00",
                },
                "dataApresentacao": "2026-11-03T00:30:00",
            },
            "/api/v2/proposicoes/123/autores": [
                {"nome": "Comissão", "proponente": "0"},
            ],
            "/api/v2/proposicoes/123/tramitacoes": [],
            "/api/v2/votacoes": [],
        }
        return httpx.Response(200, json={"dados": payloads[path]})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        camara.import_legislation(engine, client=client)
        camara.import_legislation(engine, client=client)
    with Session(engine) as session:
        propositions = session.scalars(select(Proposition)).all()
        assert len(propositions) == 1
        proposition = propositions[0]
        assert proposition.summary == "Ementa detalhada"
        assert proposition.detailed_summary == "Descrição oficial mais completa."
        assert proposition.full_text_url.endswith("/123")
        assert proposition.keywords == ["educação", "transparência"]
        assert proposition.status_description == "Aguardando despacho"
        assert proposition.status_agency == "MESA"
        assert proposition.official_detail_collected_at is not None
        assert proposition.presented_at == datetime(2026, 11, 3, 3, 30, tzinfo=timezone.utc)
        record = session.get(SourceRecord, proposition.source_record_id)
        assert record.payload["ementa"] == proposition.summary
        assert session.scalar(select(Authorship)).is_proponent is False
        assert session.scalar(select(Voting)) is None

        class Automation:
            provider = "test"
            generation_model = "generator-test"
            verification_model = "verifier-test"

            def generate(self, context):
                assert context.summary == proposition.summary
                return AssistedDraftResult(
                    plain_summary=(
                        "A proposta trata de educação e transparência. "
                        "Ela ainda precisa passar pelas etapas legislativas."
                    ),
                    what_changes="Propõe uma regra ligada à educação e à transparência.",
                    affected_groups=[],
                    practical_example=None,
                    impacts=None,
                    benefits=None,
                    cost_estimate=None,
                    analysis=None,
                )

            def verify(self, context, draft):
                return VerificationResult(
                    approved=True, grounded=True, neutral=True, clear=True, issues=[]
                )

        assert _process_one(engine, proposition.id, Automation()) == "published"
        session.expire_all()
        stored = session.scalar(
            select(PropositionCitizenExplanation).where(
                PropositionCitizenExplanation.proposition_id == proposition.id
            )
        )
        assert stored.method == "automated"
        assert stored.review_status == "published"
        assert stored.editor_name is None
        run = session.scalar(select(CitizenExplanationRun))
        assert run.status == "published"
        assert run.ai_verification["approved"] is True
        published = get_proposition(proposition.id, session).citizen_explanation
        assert published is not None
        assert published.plain_summary.startswith("A proposta trata")
        assert published.generation_model == "generator-test"

        voting = Voting(
            source="camara",
            external_id="voting-123",
            occurred_on=datetime(2026, 11, 6, tzinfo=timezone.utc).date(),
            description="Votação de uma etapa do projeto.",
            approved=True,
            source_url="https://example.test/voting-123",
            collected_at=datetime(2026, 11, 6, tzinfo=timezone.utc),
            source_record_id=record.id,
        )
        session.add(voting)
        session.flush()
        session.add(
            VotingProposition(
                voting_id=voting.id,
                proposition_id=proposition.id,
                relation_type="possible_object",
                source="camara",
                source_url=voting.source_url,
                collected_at=voting.collected_at,
                source_record_id=record.id,
            )
        )
        session.flush()
        related = get_proposition(proposition.id, session).related_votings
        assert len(related) == 1
        assert related[0].title == "Votação de uma etapa do projeto."
        assert related[0].relation_type == "possible_object"


def test_senado_author_uses_official_id_and_house_instead_of_name(engine):
    from app.api.routes.legislation import get_proposition
    from app.api.routes.parliamentarians import list_authored_propositions
    from app.modules.proposicoes.models import Authorship

    seed_people(engine, "senado")
    seen = datetime.now(timezone.utc)
    detail = {
        "id": 10,
        "codigoMateria": 42,
        "identificacao": "PL 10/2026",
        "documento": {
            "autoria": [
                {
                    "autor": "Nome usado no documento",
                    "codigoParlamentar": 1,
                    "siglaTipo": "SENADOR",
                    "casaEnte": "SF",
                    "ordem": 1,
                },
                {
                    "autor": "Pessoa 2",
                    "codigoParlamentar": 2,
                    "siglaTipo": "DEPUTADO",
                    "casaEnte": "CD",
                    "ordem": 2,
                },
            ],
        },
    }

    with Session(engine) as session, session.begin():
        run = ImportRun(job="fixture.legislation", status="success", started_at=seen)
        session.add(run)
        session.flush()
        people = {
            person.external_id: person.id for person in session.scalars(select(Parliamentarian))
        }
        for _ in range(2):
            proposal = senado.upsert_proposition(
                session, {"codigoMateria": 42, "_detail": detail}, run.id, seen
            )
        # Simula um vínculo legado, que havia sido atribuído por semelhança de nome.
        legacy = session.scalar(select(Authorship).where(Authorship.author_name == "Pessoa 2"))
        legacy.parliamentarian_id = people["2"]
        session.flush()
        assert list_authored_propositions(people["1"], limit=8, offset=0, db=session).total == 1
        assert list_authored_propositions(people["2"], limit=8, offset=0, db=session).total == 0
        public = get_proposition(proposal.id, db=session)
        assert len(public.authors) == 2
        assert {author.author_name: author.parliamentarian_id for author in public.authors} == {
            "Nome usado no documento": people["1"],
            "Pessoa 2": None,
        }
