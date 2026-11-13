"""Cliente e normalização da consulta de emendas do Portal da Transparência."""

import html
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode


PORTAL_AMENDMENTS_API_URL = (
    "https://api.portaldatransparencia.gov.br/api-de-dados/emendas"
)
PORTAL_AMENDMENTS_SOURCE_URL = "https://portaldatransparencia.gov.br/emendas/consulta"


def parse_amount(value) -> Decimal | None:
    if value in (None, ""):
        return None
    text = html.unescape(str(value)).strip().replace("R$", "").strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def amendments_query_url(author: str, year: int) -> str:
    query = urlencode({"ano": year, "nomeAutor": author})
    return f"{PORTAL_AMENDMENTS_SOURCE_URL}?{query}"


def amendments_api_params(author: str, year: int, page: int) -> dict[str, str | int]:
    return {"nomeAutor": author, "ano": year, "pagina": page}


def parse_amendments(payload: list[dict]) -> list[dict]:
    """Normaliza os campos financeiros retornados pela API oficial."""

    result = []
    for item in payload:
        code = str(item.get("codigoEmenda") or "").strip()
        if not code:
            continue
        result.append(
            {
                "code": code,
                "year": int(item["ano"]) if item.get("ano") else None,
                "author": item.get("nomeAutor") or item.get("autor"),
                "type": item.get("tipoEmenda"),
                "locality": item.get("localidadeDoGasto"),
                "committed": parse_amount(item.get("valorEmpenhado")),
                "liquidated": parse_amount(item.get("valorLiquidado")),
                "paid": parse_amount(item.get("valorPago")),
            }
        )
    return result
