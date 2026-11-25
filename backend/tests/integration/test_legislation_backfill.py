import json
import os
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

from app.db import models
from app.db.base import Base
from app.jobs import backfill_legislation as job
from app.modules.coletas.models import ImportRun
from app.modules.proposicoes.models import Proposition
from app.modules.votacoes.models import Voting
from app.modules.votacoes.models import Vote
from app.modules.parlamentares.models import Parliamentarian, Mandate


@pytest.fixture
def engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Execute scripts/test_backend.py para PostgreSQL isolado.")
    root = create_engine(url)
    schema = "test_" + uuid4().hex
    with root.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = root.execution_options(schema_translate_map={None: schema})
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        with root.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def handler(request):
    path = request.url.path
    if path.endswith("/proposicoes/2"):
        return httpx.Response(404)
    if path.endswith("/proposicoes/1"):
        return httpx.Response(200, json={"dados": {"id": 1, "siglaTipo": "PL", "numero": 1,
            "ano": 2026, "ementa": "Objeto oficial", "statusProposicao": {}}})
    if path.endswith("/autores") or path.endswith("/tramitacoes") or path.endswith("/votos"):
        return httpx.Response(200, json={"dados": []})
    if path.endswith("/votacoes/1-1"):
        return httpx.Response(200, json={"dados": {"id": "1-1", "data": "2026-11-18",
            "descricao": "Aprovado o requerimento.", "aprovacao": 1, "objetosPossiveis": [
                {"id": 1, "siglaTipo": "PL", "numero": 1, "ano": 2026, "ementa": "Objeto oficial"}]}})
    raise AssertionError(str(request.url))


def test_resume_skips_committed_records_and_preserves_unavailable(engine, tmp_path):
    path = tmp_path / "checkpoint.json"
    request = job.plan("camara", ["1", "2"], ["1-1"])
    calls = []
    def tracked(r):
        calls.append(str(r.url))
        return handler(r)
    with httpx.Client(transport=httpx.MockTransport(tracked)) as client:
        first = job.backfill(engine, request, path, max_items=1, client=client)
        assert first["counts"] == dict(success=1, pending=2, unavailable=0, failed=0)
        assert not first["coverage_complete"]
        previous = calls.count(f"{job.camara.BASE}/proposicoes/1")
        second = job.backfill(engine, request, path, client=client)
        assert second["counts"] == dict(success=2, pending=0, unavailable=1, failed=0)
        assert calls.count(f"{job.camara.BASE}/proposicoes/1") == previous
        assert job.backfill(engine, request, path, client=client)["processed"] == 0
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Proposition)) == 1
        assert db.scalar(select(func.count()).select_from(Voting)) == 1
    assert path.stat().st_mode & 0o777 == 0o600
    assert json.loads(path.read_text())["targets"]["proposition:2"]["status"] == "unavailable"


def test_failure_rolls_back_one_item_and_can_resume_without_losing_other(engine, tmp_path, monkeypatch):
    monkeypatch.setattr(job.camara.time, "sleep", lambda _: None)
    path = tmp_path / "checkpoint.json"
    request = job.plan("camara", ["1"], ["1-1"])
    failing = [True]
    def fail_then_recover(r):
        if r.url.path.endswith("/tramitacoes") and failing[0]:
            return httpx.Response(503)
        return handler(r)
    with httpx.Client(transport=httpx.MockTransport(fail_then_recover)) as client:
        result = job.backfill(engine, request, path, client=client)
        assert result["counts"]["failed"] == result["counts"]["success"] == 1
        with Session(engine) as db:
            # O registro mínimo veio da votação bem-sucedida; o detalhe da proposta falha não foi publicado.
            prop = db.scalars(select(Proposition)).one()
            assert prop.official_detail_collected_at is None
            assert db.scalar(select(func.count()).select_from(Voting)) == 1
        failing[0] = False
        result = job.backfill(engine, request, path, client=client)
        assert result["coverage_complete"]
        assert result["processed"] == 1
        with Session(engine) as db:
            assert db.scalars(select(Proposition)).one().official_detail_collected_at is not None
            assert db.scalar(select(func.count()).select_from(Voting)) == 1


def test_checkpoint_cannot_be_reused_for_a_different_plan(engine, tmp_path):
    path = tmp_path / "checkpoint.json"
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        job.backfill(engine, job.plan("camara", ["1"]), path, client=client)
        with pytest.raises(ValueError, match="outro plano"):
            job.backfill(engine, job.plan("camara", ["2"]), path, client=client)


def test_recovery_does_not_run_concurrently_with_annual_votes(engine, tmp_path):
    with engine.connect() as owner:
        owner.execute(text("SELECT pg_advisory_lock(:key)"), {"key": job.ANNUAL_VOTES_LOCK})
        owner.commit()
        try:
            with httpx.Client(transport=httpx.MockTransport(handler)) as client:
                with pytest.raises(RuntimeError, match="anual"):
                    job.backfill(engine, job.plan("camara", ["1"]), tmp_path / "busy.json", client=client)
        finally:
            owner.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": job.ANNUAL_VOTES_LOCK})
            owner.commit()


def test_crash_after_database_commit_replays_safely(engine, tmp_path, monkeypatch):
    path = tmp_path / "crash.json"
    save = job.save
    crash = [True]
    def interrupted(path, state):
        if crash[0] and any(item["status"] == "success" for item in state["targets"].values()):
            raise OSError("simulated checkpoint failure")
        save(path, state)
    monkeypatch.setattr(job, "save", interrupted)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        request = job.plan("camara", ["1"])
        with pytest.raises(OSError):
            job.backfill(engine, request, path, client=client)
        assert json.loads(path.read_text())["targets"]["proposition:1"]["status"] == "failed"
        crash[0] = False
        assert job.backfill(engine, request, path, client=client)["coverage_complete"]
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Proposition)) == 1


def test_voting_also_queues_detail_authors_and_proceedings(engine, tmp_path):
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = job.backfill(engine, job.plan("camara", voting_ids=["1-1"]),
                              tmp_path / "voting.json", client=client)
    assert result["coverage_complete"]
    assert result["counts"]["success"] == 2
    with Session(engine) as db:
        assert db.scalars(select(Proposition)).one().official_detail_collected_at is not None


def test_unmatched_individual_votes_are_reported_as_incomplete(engine, tmp_path):
    def missing_person(r):
        if r.url.path.endswith("/votos"):
            return httpx.Response(200, json={"dados": [{"voto": "Sim", "deputado_": {"id": 999}}]})
        return handler(r)
    path = tmp_path / "unmatched.json"
    with httpx.Client(transport=httpx.MockTransport(missing_person)) as client:
        result = job.backfill(engine, job.plan("camara", voting_ids=["1-1"]), path, client=client)
    assert not result["coverage_complete"]
    assert result["counts"]["failed"] == 1
    item = json.loads(path.read_text())["targets"]["voting:1-1"]
    assert item["metadata"]["vote_coverage"]["missing_parliamentarians"] == 1
    assert item["error_code"] == "incomplete_votes"


def test_senate_annual_discovery_is_not_limited_to_recent_fifty(engine, tmp_path):
    items = [{"CodigoVotacaoSve": str(n), "DataSessao": "2026-01-10", "DescricaoVotacao": "Votação nominal",
              "Resultado": "A", "Votos": {}} for n in range(1, 54)]
    calls = []
    def annual(r):
        calls.append(str(r.url))
        return httpx.Response(200, json={"ListaVotacoes": {"Votacoes": {"Votacao": items}}})
    with httpx.Client(transport=httpx.MockTransport(annual)) as client:
        request = job.plan("senado", year=2026, discover_votes=True)
        first = job.backfill(engine, request, tmp_path / "senado.json", max_items=2, client=client)
        assert first["counts"]["success"] == 2
        assert first["counts"]["pending"] == 51
        assert first["discovery_complete"] and not first["coverage_complete"]
        second = job.backfill(engine, request, tmp_path / "senado.json", max_items=100, client=client)
        assert second["coverage_complete"]
        previous_calls = len(calls)
        assert job.backfill(engine, request, tmp_path / "senado.json", client=client)["processed"] == 0
        assert len(calls) == previous_calls
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(Voting)) == 53


@pytest.mark.parametrize("valid_identity", [True, False])
def test_senate_historical_identity_requires_matching_official_profile(engine, tmp_path, valid_identity):
    code = "5732"
    profile_code = code if valid_identity else "9999"
    item = {"CodigoVotacaoSve": "4360", "DataSessao": "2026-02-24", "DescricaoVotacao": "Votação nominal",
        "Resultado": "A", "Votos": {"VotoParlamentar": [{"CodigoParlamentar": code,
            "NomeParlamentar": "Nome publicado no evento", "Voto": "Sim", "SiglaPartido": "ABC", "SiglaUF": "SP",
            "Url": f"http://www25.senado.leg.br/web/senadores/senador/-/perfil/{profile_code}"}]}}
    def annual(r):
        return httpx.Response(200, json={"ListaVotacoes": {"Votacoes": {"Votacao": [item]}}})
    request = job.plan("senado", voting_ids=["4360"], year=2026)
    with httpx.Client(transport=httpx.MockTransport(annual)) as client:
        result = job.backfill(engine, request, tmp_path / "historical.json", client=client)
        with Session(engine) as db:
            if not valid_identity:
                assert not result["coverage_complete"]
                assert db.scalar(select(func.count()).select_from(Parliamentarian)) == 0
                assert db.scalar(select(func.count()).select_from(Vote)) == 0
                return
            assert result["coverage_complete"]
            person = db.scalars(select(Parliamentarian)).one()
            assert person.external_id == code and not person.is_current
            assert person.source_url.startswith("https://www25.senado.leg.br/")
            assert db.scalar(select(func.count()).select_from(Mandate)) == 0
            assert db.scalar(select(func.count()).select_from(Vote)) == 1

        assert job.backfill(engine, request, tmp_path / "historical.json", client=client)["processed"] == 0
        with Session(engine) as db, db.begin():
            person = db.scalars(select(Parliamentarian)).one()
            person.name, person.is_current = "Nome confirmado no cadastro atual", True
        assert job.backfill(engine, request, tmp_path / "refresh.json", client=client)["coverage_complete"]
        with Session(engine) as db:
            person = db.scalars(select(Parliamentarian)).one()
            assert person.name == "Nome confirmado no cadastro atual" and person.is_current
            assert db.scalar(select(func.count()).select_from(Vote)) == 1


def test_failed_senate_checkpoint_resumes_after_historical_identity_fix(engine, tmp_path, monkeypatch):
    item = {"CodigoVotacaoSve": "4360", "DataSessao": "2026-02-24", "DescricaoVotacao": "Votação nominal",
        "Resultado": "A", "Votos": {"VotoParlamentar": [{"CodigoParlamentar": "5732",
            "NomeParlamentar": "Identidade oficial de teste", "Voto": "Sim",
            "Url": "http://www25.senado.leg.br/web/senadores/senador/-/perfil/5732"}]}}
    def annual(r):
        return httpx.Response(200, json={"ListaVotacoes": {"Votacoes": {"Votacao": [item]}}})
    path = tmp_path / "same-checkpoint.json"
    request = job.plan("senado", voting_ids=["4360"], year=2026)
    with httpx.Client(transport=httpx.MockTransport(annual)) as client:
        with monkeypatch.context() as old_version:
            old_version.setattr(job.senado, "historical_senator", lambda *args: None)
            first = job.backfill(engine, request, path, client=client)
            assert first["counts"]["failed"] == 1
        second = job.backfill(engine, request, path, client=client)
        assert second["coverage_complete"] and second["counts"]["success"] == 1
        assert job.backfill(engine, request, path, client=client)["processed"] == 0
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Parliamentarian)) == 1
        assert db.scalar(select(func.count()).select_from(Vote)) == 1
