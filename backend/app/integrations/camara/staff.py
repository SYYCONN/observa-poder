"""Consulta pública da equipe em exercício nos gabinetes da Câmara."""

import html
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode


CAMARA_STAFF_URL = "https://www.camara.leg.br/transparencia/recursos-humanos/funcionarios"


def _plain_text(value: str) -> str:
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def staff_list_url(lotacao: str) -> str:
    query = urlencode(
        {
            "search": "",
            "categoriaFuncional": "Secretário Parlamentar",
            "areaDeAtuacao": "",
            "lotacao": lotacao,
            "situacao": "Em exercício",
        }
    )
    return f"{CAMARA_STAFF_URL}?{query}"


def staff_remuneration_url(url: str, year: int, month: int) -> str:
    """Seleciona a competência na página individual de remuneração."""

    separator = "&" if "?" in url else "?"
    return f"{url}{separator}ano={year}&mes={month}"


def parse_staff_lotacoes(payload: str) -> list[str]:
    """Extrai os nomes oficiais de gabinetes disponíveis como filtro."""

    payload = html.unescape(payload)
    values = re.findall(
        r"[?&]lotacao=([^&\"]+).*?<span>(Gabinete [^<]+)</span>", payload, re.I | re.S
    )
    result: list[str] = []
    for _, label in values:
        value = _plain_text(label)
        if value.lower().startswith("gabinete ") and value not in result:
            result.append(value)
    return result


def parse_staff_count(payload: str) -> int | None:
    """Lê o total de servidores retornado pela busca oficial do gabinete."""

    text = _plain_text(payload)
    match = re.search(r"Exibindo resultados de \d+ a \d+ de (\d+) encontrados", text, re.I)
    return int(match.group(1)) if match else None


def _clean_cell(value: str) -> str:
    return re.sub(r"\s+", " ", _plain_text(value)).strip()


def _money(value: str) -> Decimal | None:
    normalized = _clean_cell(value).replace("R$", "").replace(" ", "")
    if not normalized:
        return None
    # A Câmara publica valores no padrão brasileiro, por exemplo 11.233,68.
    normalized = normalized.replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _sum_values(values: dict[str, Decimal | None], labels: tuple[str, ...]) -> Decimal | None:
    selected = [
        value
        for label, value in values.items()
        if value is not None and any(fragment in label.casefold() for fragment in labels)
    ]
    return sum(selected, Decimal("0")) if selected else None


def parse_staff_members(payload: str) -> list[dict[str, str | None]]:
    """Extrai os servidores publicados na tabela oficial do gabinete."""

    members: list[dict[str, str | None]] = []
    rows = re.findall(
        r"<tr\b[^>]*class=\"[^\"]*tabela-responsiva__linha[^\"]*\"[^>]*>(.*?)</tr>",
        payload,
        re.I | re.S,
    )
    for row in rows:
        name_match = re.search(
            r'data-th="Nome"[^>]*>.*?data-target="#([^"]+)"[^>]*>\s*([^<]+)',
            row,
            re.I | re.S,
        )
        if not name_match:
            continue
        remuneration_match = re.search(
            r'data-th="Remuneração".*?href="(https://www\.camara\.leg\.br/'
            r'transparencia/recursos-humanos/remuneracao/[^"?]+)"',
            row,
            re.I | re.S,
        )
        cells = re.findall(
            r'<td\b[^>]*data-th="([^"]+)"[^>]*>(.*?)</td>', row, re.I | re.S
        )
        cell_values = {label.casefold(): _clean_cell(value) for label, value in cells}
        token, name = name_match.groups()
        members.append(
            {
                "external_id": token,
                "name": _clean_cell(name),
                "category": cell_values.get("categoria funcional"),
                "area_of_work": cell_values.get("área de atuação"),
                "source_remuneration_url": remuneration_match.group(1)
                if remuneration_match
                else None,
            }
        )
    return members


def enrich_staff_member(payload: str, member: dict[str, str | None]) -> dict[str, str | None]:
    """Completa cargo e nível a partir do modal da linha selecionada."""

    token = re.escape(member["external_id"] or "")
    modal = re.search(rf'id="{token}".*?</div>\s*</div>\s*</div>\s*</div>', payload, re.I | re.S)
    if modal:
        modal_text = _plain_text(modal.group(0))
        for key, pattern in {
            "job_title": r"Cargo:\s*([^:]+?)(?=Nível:|$)",
            "level": r"Nível:\s*([^:]+)",
        }.items():
            match = re.search(pattern, modal_text, re.I)
            if match:
                member[key] = _clean_cell(match.group(1))
    return member


def parse_staff_remuneration(payload: str) -> dict[str, Decimal | str | None]:
    """Lê a folha mensal individual publicada pela Câmara."""

    text = _plain_text(payload)
    period_heading = re.search(
        r'<h3\b[^>]*class="[^"]*remuneracao-funcionario__mes-ano[^"]*"[^>]*>(.*?)</h3>',
        payload,
        re.I | re.S,
    )
    period_match = (
        re.match(r"(\d{2})(\d{4})\s+–\s+(.+)", _clean_cell(period_heading.group(1)))
        if period_heading
        else None
    )
    row_values: dict[str, Decimal | None] = {}
    for description, value in re.findall(
        r'<td\b[^>]*class="[^"]*tabela-responsiva__coluna--1[^"]*"[^>]*>(.*?)</td>\s*'
        r'<td\b[^>]*class="[^"]*tabela-responsiva__coluna--2[^"]*"[^>]*>(.*?)</td>',
        payload,
        re.I | re.S,
    ):
        row_values[_clean_cell(description)] = _money(value)
    gross = _sum_values(
        row_values,
        (
            "remuneração fixa",
            "vantagens de natureza pessoal",
            "função ou cargo em comissão",
            "gratificação natalina",
            "férias",
            "outras remunerações eventuais",
            "abono permanência",
        ),
    )
    net = _sum_values(row_values, ("remuneração após descontos obrigatórios",))
    allowances = _sum_values(row_values, ("diárias", "auxílios", "vantagens indenizatórias"))
    return {
        "gross_amount": gross,
        "net_amount": net,
        "allowances_amount": allowances,
        "payroll_period": f"{period_match.group(2)}-{period_match.group(1)}"
        if period_match
        else None,
        "payroll_type": period_match.group(3).strip().lower() if period_match else None,
        "exercise_date": (
            re.search(r"Data de exercício:\s*(\d{2}/\d{2}/\d{4})", text, re.I).group(1)
            if re.search(r"Data de exercício:\s*(\d{2}/\d{2}/\d{4})", text, re.I)
            else None
        ),
    }
