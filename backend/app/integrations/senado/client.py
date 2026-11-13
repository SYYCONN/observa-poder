import random
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date

import httpx

from app.core.dates import local_today


BASE_URL = "https://legis.senado.leg.br/dadosabertos/senador/lista/atual"


class SourceError(Exception):
    """Erro controlado na leitura da fonte oficial."""


@dataclass(frozen=True)
class Senator:
    external_id: str
    name: str
    photo_url: str | None
    source_url: str
    state: str
    party: str | None
    legislature: str
    legislature_start: date | None
    legislature_end: date | None

    def payload(self) -> dict:
        return {
            "external_id": self.external_id,
            "name": self.name,
            "photo_url": self.photo_url,
            "source_url": self.source_url,
            "state": self.state,
            "party": self.party,
            "legislature": self.legislature,
            "legislature_start": (
                self.legislature_start.isoformat() if self.legislature_start else None
            ),
            "legislature_end": self.legislature_end.isoformat() if self.legislature_end else None,
        }


def _text(parent: ET.Element, path: str) -> str | None:
    value = parent.findtext(path)
    return value.strip() if value else None


def _date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _https(url: str | None) -> str | None:
    return url.replace("http://", "https://", 1) if url else None


def parse_current_senators(body: bytes, today: date | None = None) -> list[Senator]:
    """Converte o XML oficial em registros mínimos e estáveis para publicação."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        raise SourceError("Resposta incompatível com o contrato de senadores.") from None
    if root.tag.rsplit("}", 1)[-1] != "ListaParlamentarEmExercicio":
        raise SourceError("Resposta incompatível com a lista de senadores.")
    today = today or local_today()
    records: list[Senator] = []
    seen: set[str] = set()
    for item in root.findall(".//Parlamentar"):
        identity = item.find("./IdentificacaoParlamentar")
        mandate = item.find("./Mandato")
        if identity is None or mandate is None:
            raise SourceError("Registro de senador sem identificação ou mandato.")
        external_id = _text(identity, "CodigoParlamentar")
        name = _text(identity, "NomeParlamentar")
        state = _text(identity, "UfParlamentar")
        source_url = _https(_text(identity, "UrlPaginaParlamentar"))
        if not external_id or not name or not state or not source_url:
            raise SourceError("Registro de senador sem campos obrigatórios.")
        if external_id in seen:
            raise SourceError("Senador duplicado na resposta oficial.")
        legislatures = []
        for path in ("PrimeiraLegislaturaDoMandato", "SegundaLegislaturaDoMandato"):
            legislature = mandate.find(path)
            if legislature is None:
                continue
            number = _text(legislature, "NumeroLegislatura")
            start = _date(_text(legislature, "DataInicio"))
            end = _date(_text(legislature, "DataFim"))
            if number:
                legislatures.append((number, start, end))
        if not legislatures:
            raise SourceError("Mandato de senador sem legislatura.")
        current = next(
            (
                entry
                for entry in legislatures
                if entry[1] and entry[1] <= today and (not entry[2] or today <= entry[2])
            ),
            None,
        )
        if current is None:
            raise SourceError("Mandato de senador sem legislatura vigente na data da coleta.")
        records.append(
            Senator(
                external_id=external_id,
                name=name,
                photo_url=_https(_text(identity, "UrlFotoParlamentar")),
                source_url=source_url,
                state=state.upper(),
                party=_text(identity, "SiglaPartidoParlamentar"),
                legislature=current[0],
                legislature_start=current[1],
                legislature_end=current[2],
            )
        )
        seen.add(external_id)
    if not records:
        raise SourceError("Lista vazia; coleta não publicada.")
    return records


class SenadoClient:
    MAX_BYTES = 2_000_000

    def __init__(self, client: httpx.Client | None = None, sleep=time.sleep):
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(20, connect=5),
            follow_redirects=False,
            headers={"Accept": "application/xml", "User-Agent": "DeOlhoNaPolitica/0.1"},
        )
        self.owns_client = client is None
        self.sleep = sleep
        self.received = 0

    def close(self):
        if self.owns_client:
            self.client.close()

    def fetch_current_senators(self) -> list[Senator]:
        for attempt in range(3):
            try:
                response = self.client.get(BASE_URL)
                if response.status_code in (429, 500, 502, 503, 504):
                    raise httpx.HTTPStatusError(
                        "retryable", request=response.request, response=response
                    )
                if response.status_code != 200:
                    raise SourceError(f"Resposta HTTP inesperada: {response.status_code}.")
                if len(response.content) > self.MAX_BYTES:
                    raise SourceError("Resposta excedeu o limite de tamanho.")
                records = parse_current_senators(response.content)
                self.received = len(records)
                return records
            except SourceError:
                raise
            except (httpx.TransportError, httpx.HTTPStatusError):
                if attempt == 2:
                    raise SourceError("Fonte indisponível após três tentativas.") from None
                self.sleep(2**attempt + random.random())
        raise AssertionError("unreachable")
