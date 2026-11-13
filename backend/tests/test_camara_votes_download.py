import httpx

from app.jobs import import_camara_votes as job


def test_annual_vote_download_retries_transient_server_error(monkeypatch):
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(200, content=b"id;descricao\n1;Teste\n", request=request)

    monkeypatch.setattr(job.time, "sleep", lambda _: None)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        path = job.download(client, "https://dadosabertos.camara.leg.br/arquivo.csv")
    try:
        assert attempts == 2
        assert path.read_text() == "id;descricao\n1;Teste\n"
    finally:
        path.unlink(missing_ok=True)
