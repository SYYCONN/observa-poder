from decimal import Decimal

from app.integrations.camara.remuneration import (
    parse_remuneration_links,
    parse_remuneration_page,
    subsidy_reference,
)
from app.jobs.import_camara_remuneration import _match_person


def test_camara_subsidy_reference_is_source_backed():
    reference = subsidy_reference("camara")

    assert reference is not None
    value, source_url, note = reference
    assert value == Decimal("46366.19")
    assert source_url.startswith("https://www.camara.leg.br/")
    assert "bruto" in note.lower()


def test_unknown_source_has_no_subsidy_reference():
    assert subsidy_reference("senado") is None


def test_parse_monthly_remuneration_page():
    payload = """
    <h3>102026 – FOLHA NORMAL</h3>
    <td>a - Remuneração Fixa</td><td>46.366,19</td>
    <td>a - Remuneração após Descontos Obrigatórios</td><td>33.807,87</td>
    """

    assert parse_remuneration_page(payload) == {
        "year": 2026,
        "month": 10,
        "fixed_amount": Decimal("46366.19"),
        "net_amount": Decimal("33807.87"),
    }


def test_parse_remuneration_links():
    payload = """
    <tr class="tabela-responsiva__linha">
      <td data-th="Nome"><a href="#">ACÁCIO FAVACHO</a></td>
      <td data-th="Remuneração"><a href="https://www.camara.leg.br/transparencia/recursos-humanos/remuneracao/abc123">Consulta</a></td>
    </tr>
    <div class="modal fade modal--funcionario">
      <span class="lista-funcionario__titulo">Unidade:</span> Gabinete Acácio Favacho </li>
    </div>
    """

    assert parse_remuneration_links(payload) == [
        (
            "Acácio Favacho",
            "https://www.camara.leg.br/transparencia/recursos-humanos/remuneracao/abc123",
        )
    ]


def test_remuneration_match_requires_unique_exact_normalized_name():
    assert _match_person("Márcio Souza", [("MARCIO SOUZA", "id-1")]) == "id-1"
    assert _match_person("Marcio Souza", [("Márcio Souza", "id-1"), ("MARCIO SOUZA", "id-2")]) is None
    assert _match_person("Marcio de Souza", [("Marcio Souza", "id-1")]) is None
