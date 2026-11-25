"""Reposição explícita e retomável de legislação oficial, em lotes limitados."""

import argparse
import fcntl
import hashlib
import json
import os
import re
import tempfile
import time
from datetime import date
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.jobs import import_legislation as camara
from app.jobs import import_senado_legislation as senado
from app.jobs.import_camara_votes import LOCK_KEY as ANNUAL_VOTES_LOCK
from app.modules.coletas.models import ImportRun
from app.modules.proposicoes.models import ProceedingsEvent

MAX_BYTES = 64 * 1024**2
MAX_TARGETS = 50000


class SourceClient(httpx.Client):
    def get(self, url, **kwargs):
        time.sleep(0.25)
        with self.stream("GET", url, **kwargs) as response:
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("Resposta oficial excedeu o limite de tamanho.")
                chunks.append(chunk)
            return httpx.Response(response.status_code, headers={k: v for k, v in response.headers.items() if k.lower() not in {"content-encoding", "content-length"}},
                                  content=b"".join(chunks), request=response.request)


def save(path, state):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            os.chmod(temporary, 0o600)
            json.dump(state, output, ensure_ascii=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def plan(source, proposition_ids=(), voting_ids=(), start=None, end=None, year=None, discover_votes=False):
    if source not in {"camara", "senado"}:
        raise ValueError("Fonte inválida.")
    for identifier in proposition_ids:
        if not re.fullmatch(r"[1-9]\d{0,19}", identifier):
            raise ValueError("Identificador de proposição inválido.")
    for identifier in voting_ids:
        pattern = r"[1-9]\d{0,19}-[1-9]\d{0,9}" if source == "camara" else r"[1-9]\d{0,19}"
        if not re.fullmatch(pattern, identifier):
            raise ValueError("Identificador de votação inválido.")
    if (start is None) != (end is None):
        raise ValueError("Informe início e fim do período juntos.")
    if start and (end < start or (end - start).days > 30):
        raise ValueError("Use períodos de até 31 dias.")
    if source == "camara" and discover_votes:
        raise ValueError("Descoberta anual é do Senado; use identificadores ou períodos na Câmara.")
    if source == "senado" and (voting_ids or discover_votes) and not (1900 <= (year or 0) <= 2100):
        raise ValueError("Votações do Senado exigem o ano da sessão.")
    if source == "senado" and start and (start.year != year or end.year != year):
        raise ValueError("Divida a descoberta do Senado por ano da sessão.")
    if source == "senado" and start and not discover_votes:
        raise ValueError("Período do Senado exige descoberta de votações anuais; matérias usam identificadores.")
    if not (proposition_ids or voting_ids or start or discover_votes):
        raise ValueError("Informe identificadores ou um período para recuperar.")
    return dict(source=source, proposition_ids=sorted(set(proposition_ids)), voting_ids=sorted(set(voting_ids)),
                start=start.isoformat() if start else None, end=end.isoformat() if end else None,
                year=year, discover_votes=discover_votes)


def queue(state, kind, identifier, metadata=None):
    key = f"{kind}:{identifier}"
    if key not in state["targets"]:
        if len(state["targets"]) >= MAX_TARGETS:
            raise ValueError("Plano excedeu o limite; divida o período.")
        state["targets"][key] = dict(kind=kind, id=identifier, status="pending", attempts=0, metadata=metadata or {})
        return key
    return None


def senate_votes(client, year):
    payload = camara.get_json(client, f"{senado.BASE}/plenario/votacao/nominal/{year}")
    if not isinstance(payload.get("ListaVotacoes"), dict):
        raise ValueError("Resposta anual do Senado não contém a estrutura esperada.")
    data = payload.get("ListaVotacoes", {}).get("Votacoes", {}).get("Votacao", [])
    return {str(item.get("CodigoVotacaoSve") or item.get("CodigoSessaoVotacao")): item
            for item in senado._as_list(data)
            if str(item.get("CodigoVotacaoSve") or item.get("CodigoSessaoVotacao") or "").isdigit()}


def discover(client, state, pages, annual, checkpoint=None):
    p = state["plan"]
    if p["source"] == "senado":
        if not state["discovery_done"]:
            for identifier, item in annual.items():
                occurred = item.get("DataSessao", "")
                if not p["start"] or p["start"] <= occurred <= p["end"]:
                    queue(state, "voting", identifier)
            state["discovery_done"] = True
        return
    if not p["start"]:
        state["discovery_done"] = True
        return
    for kind, endpoint, start_key, end_key in [
        ("proposition", "proposicoes", "dataApresentacaoInicio", "dataApresentacaoFim"),
        ("voting", "votacoes", "dataInicio", "dataFim"),
    ]:
        for _ in range(pages):
            page = state["pages"].get(kind, 1)
            if page is None:
                break
            payload = camara.get_json(client, f"{camara.BASE}/{endpoint}", params={
                start_key: p["start"], end_key: p["end"], "pagina": page, "itens": 100,
                "ordem": "ASC", "ordenarPor": "id" if kind == "proposition" else "dataHoraRegistro",
            })
            items = payload.get("dados")
            if not isinstance(items, list) or len(items) > 100:
                raise ValueError("Página oficial inválida.")
            for item in items:
                identifier = str(item["id"])
                # Validar antes de construir qualquer URL com o identificador externo.
                plan("camara", [identifier] if kind == "proposition" else [], [identifier] if kind == "voting" else [])
                queue(state, kind, identifier, {"proposicaoObjeto": item["proposicaoObjeto"]} if item.get("proposicaoObjeto") is not None else {})
            has_next = any(link.get("rel") == "next" for link in payload.get("links", []))
            if not items and has_next:
                raise ValueError("Paginação oficial não avançou.")
            state["pages"][kind] = page + 1 if has_next else None
            if checkpoint:
                save(checkpoint, state)
    state["discovery_done"] = all(state["pages"].get(kind) is None for kind in ("proposition", "voting"))


def recover_item(session, client, source, target, run_id, seen, annual, year):
    coverage = {}
    identifier = target["id"]
    if source == "senado":
        if target["kind"] == "voting":
            if identifier not in annual:
                return "unavailable"
            senado.upsert_voting(session, client, annual[identifier], run_id, seen, year, coverage=coverage)
            code = annual[identifier].get("CodigoMateria")
            target["metadata"]["related_propositions"] = [str(code)] if str(code or "").isdigit() else []
            target["metadata"]["vote_coverage"] = coverage
            if coverage["missing_parliamentarians"] or coverage["unrecognized_positions"]:
                return "failed"
        else:
            item = senado.enrich_proposition(client, {"codigoMateria": identifier})
            if not item.get("_detail"):
                raise ValueError("Matéria sem detalhe oficial; preservado o último registro.")
            senado.upsert_proposition(session, item, run_id, seen)
        return "success"
    if target["kind"] == "voting":
        item = camara.get_json(client, f"{camara.BASE}/votacoes/{identifier}")["dados"]
        if str(item.get("id")) != identifier:
            raise ValueError("Identificador retornado difere do solicitado.")
        related = item.get("objetosPossiveis", []) + item.get("proposicoesAfetadas", [])
        target["metadata"]["related_propositions"] = sorted({str(obj["id"]) for obj in related if str(obj.get("id", "")).isdigit()})
        camara.upsert_voting(session, client, {**item, **target["metadata"]}, run_id, seen, coverage=coverage)
        target["metadata"]["vote_coverage"] = coverage
        if coverage["missing_parliamentarians"] or coverage["unrecognized_positions"]:
            return "failed"
        return "success"
    row = camara.enrich_known_proposition(session, client, {"id": identifier}, run_id, seen)
    if row is None:
        return "unavailable"
    events = camara.get_json(client, f"{camara.BASE}/proposicoes/{identifier}/tramitacoes")["dados"]
    for item in events:
        key = str(item.get("sequencia"))
        origin = camara.record(session, run_id, "tramitacao", f"{identifier}:{key}",
                               f"{camara.BASE}/proposicoes/{identifier}/tramitacoes", item, seen)
        event = session.scalar(select(ProceedingsEvent).where(
            ProceedingsEvent.proposition_id == row.id, ProceedingsEvent.source == "camara",
            ProceedingsEvent.external_key == key))
        if event is None:
            event = ProceedingsEvent(proposition_id=row.id, source="camara", external_key=key)
            session.add(event)
        event.occurred_at, event.sequence = camara.dt(item.get("dataHora")), item.get("sequencia")
        event.description, event.situation = item.get("descricaoTramitacao"), item.get("descricaoSituacao")
        event.agency_url, event.dispatch = item.get("uriOrgao"), item.get("despacho")
        event.rapporteur_url = item.get("uriUltimoRelator")
        event.source_url, event.source_record_id, event.collected_at = origin.source_url, origin.id, seen
    return "success"


def backfill(engine, request, checkpoint, max_items=10, pages=1, client=None, retry_errors=False):
    if not 1 <= max_items <= 100 or not 1 <= pages <= 5:
        raise ValueError("Lote ou quantidade de páginas fora do limite.")
    path = Path(checkpoint)
    if path.is_symlink() or not path.parent.is_dir():
        raise ValueError("Use diretório persistente existente e arquivo sem link simbólico.")
    owns = client is None
    client = client or SourceClient(timeout=httpx.Timeout(30, connect=10), follow_redirects=True,
        headers={"Accept": "application/json", "User-Agent": "ObservaPoder/0.1 (+https://observapoder.com.br/fontes-e-privacidade)"})
    digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    key = camara.LOCK_KEY if request["source"] == "camara" else senado.LOCK_KEY
    run_id = uuid4()
    try:
        with open(str(path) + ".lock", "a") as guard, engine.connect() as lock:
            fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if not lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}):
                raise RuntimeError("Existe outra coleta desta fonte em execução.")
            lock.commit()
            annual_locked = False
            try:
                if request["source"] == "camara":
                    if not lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": ANNUAL_VOTES_LOCK}):
                        raise RuntimeError("Existe uma carga anual de votos em execução.")
                    annual_locked = True
                    lock.commit()
                if path.exists() and path.stat().st_size > 32 * 1024**2:
                    raise ValueError("Checkpoint excedeu o limite de tamanho.")
                state = json.loads(path.read_text()) if path.exists() else dict(
                    format=1, fingerprint=digest, plan=request, pages={}, targets={},
                    discovery_done=not(request["start"] or request["discover_votes"]))
                if state.get("format") != 1 or state.get("fingerprint") != digest:
                    raise ValueError("Checkpoint pertence a outro plano; use outro arquivo.")
                for kind, ids in [("proposition", request["proposition_ids"]), ("voting", request["voting_ids"])]:
                    for identifier in ids:
                        queue(state, kind, identifier)
                if retry_errors:
                    for item in state["targets"].values():
                        if item["status"] in {"unavailable", "failed"}:
                            item.update(status="pending", attempts=0)
                with Session(engine) as session, session.begin():
                    session.execute(update(ImportRun).where(ImportRun.job == f"{request['source']}.legislation_backfill", ImportRun.status == "running").values(status="interrupted", finished_at=camara.now(), error_code="interrupted"))
                    session.add(ImportRun(id=run_id, job=f"{request['source']}.legislation_backfill",
                                         status="running", started_at=camara.now()))
                try:
                    need_annual = request["source"] == "senado" and (
                        (request["discover_votes"] and not state["discovery_done"]) or any(
                            item["kind"] == "voting" and item["status"] not in {"success", "unavailable"}
                            and item["attempts"] < 3 for item in state["targets"].values()
                        )
                    )
                    annual = senate_votes(client, request["year"]) if need_annual else {}
                    discover(client, state, pages, annual, path)
                    save(path, state)
                    processed = 0
                    candidates = list(state["targets"].values())
                    for item in candidates:
                        if processed >= max_items:
                            break
                        if item["status"] in {"success", "unavailable"} or item["attempts"] >= 3:
                            continue
                        processed += 1
                        item["attempts"] += 1
                        item.update(status="failed", error_code="interrupted")
                        save(path, state)
                        try:
                            with Session(engine) as session, session.begin():
                                item["status"] = recover_item(session, client, request["source"], item, run_id, camara.now(), annual, request["year"])
                            if item["status"] == "success":
                                item.pop("error_code", None)
                            elif item["status"] == "failed":
                                item["error_code"] = "incomplete_votes"
                            else:
                                item["error_code"] = "source_unavailable"
                        except Exception as exc:
                            item["status"] = "unavailable" if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 404 else "failed"
                            item["error_code"] = f"http_{exc.response.status_code}" if isinstance(exc, httpx.HTTPStatusError) else type(exc).__name__
                        if item["status"] in {"success", "failed"}:
                            for identifier in item["metadata"].get("related_propositions", []):
                                child = queue(state, "proposition", identifier)
                                if child:
                                    candidates.append(state["targets"][child])
                        save(path, state)
                    counts = {status: sum(x["status"] == status for x in state["targets"].values())
                              for status in ("success", "pending", "unavailable", "failed")}
                    with Session(engine) as session, session.begin():
                        run = session.get(ImportRun, run_id)
                        run.status = "failed" if counts["failed"] else "success"
                        run.finished_at, run.received = camara.now(), processed
                        run.error_code = "items_failed" if counts["failed"] else None
                    return dict(run_id=str(run_id), processed=processed, counts=counts,
                        discovery_complete=state["discovery_done"],
                        coverage_complete=state["discovery_done"] and not any(counts[k] for k in ("pending", "failed", "unavailable")))
                except Exception as exc:
                    with Session(engine) as session, session.begin():
                        run = session.get(ImportRun, run_id)
                        run.status, run.finished_at, run.error_code = "failed", camara.now(), type(exc).__name__
                    raise
            finally:
                if annual_locked:
                    lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": ANNUAL_VOTES_LOCK})
                lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                lock.commit()
    finally:
        if owns:
            client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["camara", "senado"], required=True)
    parser.add_argument("--proposition-id", action="append", default=[])
    parser.add_argument("--voting-id", action="append", default=[])
    parser.add_argument("--from-date", type=date.fromisoformat)
    parser.add_argument("--to-date", type=date.fromisoformat)
    parser.add_argument("--year", type=int)
    parser.add_argument("--discover-votings", action="store_true")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--max-items", type=int, default=10)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--retry-errors", action="store_true")
    args = parser.parse_args()
    request = plan(args.source, args.proposition_id, args.voting_id, args.from_date, args.to_date, args.year, args.discover_votings)
    try:
        result = backfill(get_engine(), request, args.checkpoint, args.max_items, args.pages,
                          retry_errors=args.retry_errors)
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_code": type(exc).__name__}))
        raise SystemExit(1) from None
    print(json.dumps(result, ensure_ascii=False))
    if result["counts"]["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
