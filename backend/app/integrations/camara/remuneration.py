"""Referências públicas de remuneração da Câmara dos Deputados.

O portal da Câmara publica o subsídio nominal de referência para deputados,
mas esse valor não representa o líquido individual recebido por cada pessoa.
Descontos, faltas e outras parcelas devem ser consultados na folha oficial.
"""

import html
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

import httpx


CAMARA_DEPUTY_REMUNERATION_URL = (
    "https://www.camara.leg.br/transparencia/recursos-humanos/funcionarios"
    "?search=&categoriaFuncional=Deputado&areaDeAtuacao=&situacao=Em%20exerc%C3%ADcio"
)

# Valor nominal mensal publicado pela Câmara na seção de remuneração.
CAMARA_DEPUTY_SUBSIDY_REFERENCE = Decimal("46366.19")
CAMARA_DEPUTY_SUBSIDY_NOTE = (
    "Valor bruto nominal de referência publicado pela Câmara. "
    "A remuneração efetiva pode variar por descontos e comparecimento."
)
CAMARA_REMUNERATION_LIST_URL = (
    "https://www.camara.leg.br/transparencia/recursos-humanos/funcionarios"
)


def subsidy_reference(source: str) -> tuple[Decimal, str, str] | None:
    """Retorna a referência de subsídio da fonte parlamentar, quando disponível."""

    if source != "camara":
        return None
    return (
        CAMARA_DEPUTY_SUBSIDY_REFERENCE,
        CAMARA_DEPUTY_REMUNERATION_URL,
        CAMARA_DEPUTY_SUBSIDY_NOTE,
    )


def _plain_text(value: str) -> str:
    value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _amount_after(text: str, label: str) -> Decimal | None:
    match = re.search(rf"{re.escape(label)}\s+(-?[\d.]+(?:,\d{{1,2}})?)", text)
    if not match:
        return None
    try:
        return Decimal(match.group(1).replace(".", "").replace(",", "."))
    except InvalidOperation:
        return None


def parse_remuneration_page(payload: str) -> dict[str, Decimal | int | str | None]:
    """Extrai somente as linhas publicadas e necessárias para a leitura do perfil."""

    text = _plain_text(payload)
    period = re.search(r"\b(0?[1-9]|1[0-2])\s*(20\d{2})\s*[–-]\s*FOLHA", text, re.I)
    fixed = _amount_after(text, "a - Remuneração Fixa")
    net = _amount_after(text, "a - Remuneração após Descontos Obrigatórios")
    return {
        "year": int(period.group(2)) if period else None,
        "month": int(period.group(1)) if period else None,
        "fixed_amount": fixed,
        "net_amount": net,
    }


def parse_remuneration_links(payload: str) -> list[tuple[str, str]]:
    """Lê nome e endereço oficial de remuneração da tabela de deputados."""

    rows = re.findall(r'<tr class="tabela-responsiva__linha">(.*?)</tr>', payload, re.S | re.I)
    units = re.findall(
        r'<span\s+class="lista-funcionario__titulo">Unidade:</span>(.*?)</li>',
        payload,
        re.S | re.I,
    )
    result: list[tuple[str, str]] = []
    for index, row in enumerate(rows):
        name_match = re.search(r'data-th="Nome".*?>(.*?)</a>', row, re.S | re.I)
        url_match = re.search(
            r'href="(https://www\.camara\.leg\.br/transparencia/recursos-humanos/remuneracao/[^"?]+)"',
            row,
            re.I,
        )
        if not name_match or not url_match:
            continue
        name = _plain_text(name_match.group(1))
        if index < len(units):
            unit = _plain_text(units[index])
            if unit.lower().startswith("gabinete "):
                name = unit[9:].strip()
        if name:
            result.append((name, url_match.group(1)))
    return result


def remuneration_list_url(page: int) -> str:
    query = urlencode(
        {
            "search": "",
            "categoriaFuncional": "Deputado",
            "areaDeAtuacao": "",
            "situacao": "Em exercício",
            "pagina": page,
        }
    )
    return f"{CAMARA_REMUNERATION_LIST_URL}?{query}"


def remuneration_month_url(base_url: str, year: int, month: int) -> str:
    return f"{base_url}?ano={year}&mes={month}"
