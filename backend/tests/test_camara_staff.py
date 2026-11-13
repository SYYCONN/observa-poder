from decimal import Decimal

from app.integrations.camara.staff import (
    enrich_staff_member,
    parse_staff_count,
    parse_staff_lotacoes,
    parse_staff_members,
    parse_staff_remuneration,
    staff_list_url,
    staff_remuneration_url,
)
from app.jobs.import_camara_staff import _match_lotacao


def test_parse_staff_count():
    assert parse_staff_count("Exibindo resultados de 1 a 14 de 14 encontrados") == 14


def test_parse_staff_count_without_result_is_zero():
    assert parse_staff_count("Exibindo resultados de 0 a 0 de 0 encontrados") == 0


def test_parse_staff_lotacoes():
    payload = """
    <a href="?categoriaFuncional=Secretário Parlamentar&amp;lotacao=Gabinete%20Acácio%20Favacho">
      <span>Gabinete Acácio Favacho</span>
    </a>
    """
    assert parse_staff_lotacoes(payload) == ["Gabinete Acácio Favacho"]


def test_staff_list_url_contains_official_filters():
    url = staff_list_url("Gabinete Acácio Favacho")
    assert "categoriaFuncional=Secret%C3%A1rio+Parlamentar" in url
    assert "lotacao=Gabinete+Ac%C3%A1cio+Favacho" in url


def test_parse_staff_members_and_modal_details():
    payload = """
    <tr class="tabela-responsiva__linha">
      <td data-th="Nome"><a data-target="#staff-1">ALINE MARIA PEREIRA</a></td>
      <td data-th="Categoria funcional">Secretário Parlamentar</td>
      <td data-th="Área de atuação">Gabinetes dos Deputados</td>
      <td data-th="Remuneração"><a href="https://www.camara.leg.br/transparencia/recursos-humanos/remuneracao/staff-1">Consulta</a></td>
    </tr>
    <div id="staff-1"><span>Cargo:</span> SECRETÁRIO PARLAMENTAR
      <span>Nível:</span> SP16</div></div></div></div>
    """
    member = parse_staff_members(payload)[0]
    enrich_staff_member(payload, member)
    assert member["name"] == "ALINE MARIA PEREIRA"
    assert member["level"] == "SP16"
    assert member["source_remuneration_url"].endswith("staff-1")


def test_parse_staff_remuneration_values():
    payload = """
    <h3 class="remuneracao-funcionario__mes-ano">102026 – FOLHA NORMAL</h3>
    <li>Data de exercício: 24/02/2023</li>
    <td class="tabela-responsiva__coluna--1">a - Função ou Cargo em Comissão</td>
    <td class="tabela-responsiva__coluna--2">11.233,68</td>
    <td class="tabela-responsiva__coluna--1">a - Remuneração após Descontos Obrigatórios</td>
    <td class="tabela-responsiva__coluna--2">8.336,80</td>
    <td class="tabela-responsiva__coluna--1">b - Auxílios</td>
    <td class="tabela-responsiva__coluna--2">1.860,44</td>
    """
    values = parse_staff_remuneration(payload)
    assert values["gross_amount"] == Decimal("11233.68")
    assert values["net_amount"] == Decimal("8336.80")
    assert values["allowances_amount"] == Decimal("1860.44")
    assert values["payroll_type"] == "folha normal"
    assert values["exercise_date"] == "24/02/2023"


def test_staff_remuneration_url_selects_competence():
    assert staff_remuneration_url("https://camara.test/remuneracao/1", 2026, 10).endswith(
        "?ano=2026&mes=10"
    )


def test_staff_match_requires_unique_exact_normalized_name():
    assert _match_lotacao("Acácio Favacho", ["Gabinete Acácio Favacho"]) == "Gabinete Acácio Favacho"
    assert _match_lotacao("Acácio Fava", ["Gabinete Acácio Favacho"]) is None
    assert _match_lotacao(
        "Acácio Favacho", ["Gabinete Acácio Favacho", "Gabinete Acacio Favacho"]
    ) is None


def test_staff_parser_rejects_non_official_remuneration_link():
    payload = """
    <tr class="tabela-responsiva__linha">
      <td data-th="Nome"><a data-target="#staff-1">PESSOA EXEMPLO</a></td>
      <td data-th="Remuneração"><a href="https://example.test/remuneracao/staff-1">Consulta</a></td>
    </tr>
    """
    assert parse_staff_members(payload)[0]["source_remuneration_url"] is None
