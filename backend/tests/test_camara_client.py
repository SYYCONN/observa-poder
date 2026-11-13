import httpx
import pytest

from app.integrations.camara.client import CamaraClient, SourceError
from app.integrations.camara.schemas import BASE_URL


def deputy(identifier=1, **changes):
    return {
        "id": identifier,
        "uri": f"{BASE_URL}/deputados/{identifier}",
        "nome": "Pessoa Teste",
        "siglaUf": "SP",
        "siglaPartido": "TESTE",
        "uriPartido": f"{BASE_URL}/partidos/1",
        "idLegislatura": 57,
        "urlFoto": None,
        **changes,
    }


def page(records, number=1, last=1):
    def link(n):
        return f"{BASE_URL}/deputados?pagina={n}&itens=100&ordem=ASC&ordenarPor=id"

    links = [{"rel": "self", "href": link(number)}, {"rel": "last", "href": link(last)}]
    if number < last:
        links.append({"rel": "next", "href": link(number + 1)})
    return {"dados": records, "links": links}


def make_client(handler, sleep=lambda _: None):
    return CamaraClient(httpx.Client(transport=httpx.MockTransport(handler)), sleep=sleep)


def test_pagination_and_data_minimization():
    calls = []

    def handler(request):
        calls.append(int(request.url.params["pagina"]))
        records = (
            [deputy(i, email="private@example.invalid", cpf="not-collected") for i in range(1, 101)]
            if len(calls) == 1
            else [deputy(101)]
        )
        return httpx.Response(200, json=page(records, len(calls), 2))

    client = make_client(handler)
    records = client.fetch_current_deputies()
    assert calls == [1, 2]
    assert len(records) == 101
    assert "email" not in records[0].model_dump()
    assert "cpf" not in records[0].model_dump()
    assert records[-1]._page_number == 2


def test_rate_limit_retries_and_respects_retry_after():
    calls, sleeps = [], []

    def handler(request):
        calls.append(request)
        return (
            httpx.Response(429, headers={"Retry-After": "5"})
            if len(calls) == 1
            else httpx.Response(200, json=page([deputy()]))
        )

    records = make_client(handler, sleeps.append).fetch_current_deputies()
    assert len(records) == 1
    assert len(calls) == 2
    assert sleeps == [5]


@pytest.mark.parametrize("status", [429, 500, 503])
def test_retry_limit(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status)

    with pytest.raises(SourceError, match="três tentativas"):
        make_client(handler).fetch_current_deputies()
    assert len(calls) == 3


@pytest.mark.parametrize(
    "body",
    [
        page([]),
        page([deputy(1), deputy(1)]),
        page([deputy(siglaUf="XX")]),
        page([deputy(id="1")]),
        page([deputy(uri="https://evil.invalid")]),
        {"dados": [deputy()]},
    ],
)
def test_invalid_payload_not_accepted(body):
    with pytest.raises(SourceError):
        make_client(lambda _: httpx.Response(200, json=body)).fetch_current_deputies()


def test_external_pagination_url_rejected_without_requesting_it():
    body = page([deputy()])
    body["links"][0]["href"] = "http://169.254.169.254/metadata"
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=body)

    with pytest.raises(SourceError, match="endpoint permitido"):
        make_client(handler).fetch_current_deputies()
    assert len(calls) == 1


def test_incomplete_pagination_rejected():
    body = page([deputy(i) for i in range(1, 101)], last=2)
    body["links"] = [link for link in body["links"] if link["rel"] != "next"]
    with pytest.raises(SourceError, match="incompleta"):
        make_client(lambda _: httpx.Response(200, json=body)).fetch_current_deputies()


def test_large_payload_rejected():
    client = make_client(lambda _: httpx.Response(200, content=b"x" * 100))
    client.MAX_BYTES = 10
    with pytest.raises(SourceError, match="tamanho"):
        client.fetch_current_deputies()


def test_transport_failure_retries():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ConnectTimeout("temporary")

    with pytest.raises(SourceError):
        make_client(handler).fetch_current_deputies()
    assert len(calls) == 3


def test_redirect_not_followed():
    with pytest.raises(SourceError, match="302"):
        make_client(
            lambda _: httpx.Response(302, headers={"Location": "http://localhost"})
        ).fetch_current_deputies()


def test_profile_and_history_use_only_public_contract_fields():
    def handler(request):
        if request.url.path.endswith("/historico"):
            return httpx.Response(
                200,
                json={
                    "dados": [
                        {
                            "id": 220705,
                            "idLegislatura": 57,
                            "dataHora": "2023-02-01T12:05:00",
                            "situacao": "Exercício",
                            "descricaoStatus": "Entrada - Posse de Eleito Titular",
                            "email": "discard@example.invalid",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "dados": {
                    "id": 220705,
                    "nomeCivil": "DELTAN MARTINAZZO DALLAGNOL",
                    "dataNascimento": "1980-01-15",
                    "cpf": "must-be-discarded",
                }
            },
        )

    profile, history = make_client(handler).fetch_deputy_profile(220705)
    assert profile.dataNascimento.isoformat() == "1980-01-15"
    assert "cpf" not in profile.model_dump()
    assert history[0].dataHora.date().isoformat() == "2023-02-01"
    assert "email" not in history[0].model_dump()


def test_profile_rejects_mismatched_identifier():
    with pytest.raises(SourceError, match="diverge"):
        make_client(
            lambda _: httpx.Response(
                200,
                json={
                    "dados": {
                        "id": 2,
                        "nomeCivil": "Outra pessoa",
                        "dataNascimento": None,
                    }
                },
            )
        ).fetch_deputy_profile(1)


def test_bulk_profiles_and_history_are_normalized():
    def handler(request):
        if "deputadosHistorico" in request.url.path:
            return httpx.Response(
                200,
                json={
                    "dados": [
                        {
                            "ide_cadastro": "220705",
                            "datIni": "2023-02-01 12:05:00.0",
                            "num_legislatura": 57,
                            "situacao": "Exercício",
                            "descricao": "Entrada - Posse de Eleito Titular",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "dados": [
                    {
                        "uri": f"{BASE_URL}/deputados/220705",
                        "nomeCivil": "DELTAN MARTINAZZO DALLAGNOL",
                        "dataNascimento": "1980-01-15",
                    }
                ]
            },
        )

    profiles, histories = make_client(handler).fetch_deputy_profiles_bulk()
    assert profiles[220705].dataNascimento.isoformat() == "1980-01-15"
    assert histories[220705][0].descricaoStatus.startswith("Entrada -")
    assert histories[220705][0].dataHora.date().isoformat() == "2023-02-01"
