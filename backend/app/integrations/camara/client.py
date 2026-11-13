import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, urlsplit

import httpx
from pydantic import ValidationError

from app.integrations.camara.schemas import (
    BASE_URL,
    BulkDeputyHistoryResponse,
    BulkDeputyProfilesResponse,
    DeputiesPage,
    DeputyHistoryResponse,
    DeputyProfileResponse,
)


class SourceError(Exception):
    """Mensagem controlada, sem corpo remoto, parâmetros pessoais ou credenciais."""


class CamaraClient:
    PAGE_SIZE = 100
    MAX_PAGES = 100
    MAX_BYTES = 2_000_000
    BULK_MAX_BYTES = 50_000_000
    PROFILES_BULK_URL = f"{BASE_URL.removesuffix('/api/v2')}/arquivos/deputados/json/deputados.json"
    HISTORY_BULK_URL = (
        f"{BASE_URL.removesuffix('/api/v2')}/arquivos/deputadosHistorico/json/"
        "deputadosHistorico.json"
    )

    def __init__(self, client: httpx.Client | None = None, sleep=time.sleep):
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(20, connect=5),
            follow_redirects=False,
            headers={"Accept": "application/json", "User-Agent": "DeOlhoNaPolitica/0.1"},
        )
        self.owns_client = client is None
        self.sleep = sleep
        self.pages = 0
        self.received = 0

    def close(self):
        if self.owns_client:
            self.client.close()

    def _retry_delay(self, value: str | None, attempt: int) -> float:
        delay = 2**attempt + random.random()
        if value:
            try:
                seconds = float(value)
            except ValueError:
                try:
                    seconds = (
                        parsedate_to_datetime(value) - datetime.now(timezone.utc)
                    ).total_seconds()
                except (TypeError, ValueError, OverflowError):
                    seconds = 0
            if seconds > 60:
                raise SourceError(
                    "Fonte solicitou espera superior a 60 segundos; executar novamente mais tarde."
                )
            delay = max(delay, seconds)
        return max(0, delay)

    def _request_page(self, page: int) -> DeputiesPage:
        for attempt in range(3):
            retry_after = None
            try:
                with self.client.stream(
                    "GET",
                    BASE_URL + "/deputados",
                    params={
                        "pagina": page,
                        "itens": self.PAGE_SIZE,
                        "ordem": "ASC",
                        "ordenarPor": "id",
                    },
                ) as response:
                    if response.status_code in (429, 500, 502, 503, 504):
                        retry_after = response.headers.get("Retry-After")
                    else:
                        if response.status_code != 200:
                            raise SourceError(f"Resposta HTTP inesperada: {response.status_code}.")
                        chunks = bytearray()
                        for chunk in response.iter_bytes():
                            chunks.extend(chunk)
                            if len(chunks) > self.MAX_BYTES:
                                raise SourceError("Resposta excedeu o limite de tamanho.")
                        try:
                            return DeputiesPage.model_validate_json(chunks)
                        except ValidationError:
                            raise SourceError(
                                "Resposta incompatível com o contrato de deputados."
                            ) from None
            except httpx.TransportError:
                pass
            if attempt == 2:
                raise SourceError("Fonte indisponível após três tentativas.")
            self.sleep(self._retry_delay(retry_after, attempt))
        raise AssertionError("unreachable")

    def _request_detail(self, identifier: int, suffix: str, schema):
        path = f"/deputados/{identifier}{suffix}"
        for attempt in range(3):
            retry_after = None
            try:
                with self.client.stream("GET", BASE_URL + path) as response:
                    if response.status_code in (429, 500, 502, 503, 504):
                        retry_after = response.headers.get("Retry-After")
                    else:
                        if response.status_code != 200:
                            raise SourceError(f"Resposta HTTP inesperada: {response.status_code}.")
                        chunks = bytearray()
                        for chunk in response.iter_bytes():
                            chunks.extend(chunk)
                            if len(chunks) > self.MAX_BYTES:
                                raise SourceError("Resposta excedeu o limite de tamanho.")
                        try:
                            result = schema.model_validate_json(chunks)
                        except ValidationError:
                            raise SourceError(
                                "Resposta incompatível com o contrato de detalhes do deputado."
                            ) from None
                        records = [result.dados] if not isinstance(result.dados, list) else result.dados
                        if any(record.id != identifier for record in records):
                            raise SourceError("Identificador do detalhe diverge do solicitado.")
                        return result
            except httpx.TransportError:
                pass
            if attempt == 2:
                raise SourceError("Fonte indisponível após três tentativas.")
            self.sleep(self._retry_delay(retry_after, attempt))
        raise AssertionError("unreachable")

    def fetch_deputy_profile(self, identifier: int):
        detail = self._request_detail(identifier, "", DeputyProfileResponse).dados
        history = self._request_detail(identifier, "/historico", DeputyHistoryResponse).dados
        return detail, history

    def _request_bulk(self, url: str, schema):
        for attempt in range(3):
            retry_after = None
            try:
                with self.client.stream("GET", url) as response:
                    if response.status_code in (429, 500, 502, 503, 504):
                        retry_after = response.headers.get("Retry-After")
                    else:
                        if response.status_code != 200:
                            raise SourceError(f"Resposta HTTP inesperada: {response.status_code}.")
                        chunks = bytearray()
                        for chunk in response.iter_bytes():
                            chunks.extend(chunk)
                            if len(chunks) > self.BULK_MAX_BYTES:
                                raise SourceError("Arquivo em lote excedeu o limite de tamanho.")
                        try:
                            return schema.model_validate_json(chunks)
                        except (ValidationError, ValueError):
                            raise SourceError(
                                "Arquivo em lote incompatível com o contrato de deputados."
                            ) from None
            except httpx.TransportError:
                pass
            if attempt == 2:
                raise SourceError("Fonte em lote indisponível após três tentativas.")
            self.sleep(self._retry_delay(retry_after, attempt))
        raise AssertionError("unreachable")

    def fetch_deputy_profiles_bulk(self):
        profile_rows = self._request_bulk(self.PROFILES_BULK_URL, BulkDeputyProfilesResponse).dados
        history_rows = self._request_bulk(self.HISTORY_BULK_URL, BulkDeputyHistoryResponse).dados
        profiles = {}
        for profile in profile_rows:
            try:
                identifier = profile.id
            except ValueError:
                raise SourceError("Arquivo de perfis contém URI inválida.") from None
            if identifier in profiles:
                raise SourceError("Arquivo de perfis contém deputado duplicado.")
            profiles[identifier] = profile
        histories = {}
        for row in history_rows:
            histories.setdefault(int(row.ide_cadastro), []).append(row.normalized())
        return profiles, histories

    def _link_page(self, href: str) -> int:
        url = urlsplit(href)
        if (
            url.scheme != "https"
            or url.netloc != "dadosabertos.camara.leg.br"
            or url.path != "/api/v2/deputados"
            or url.fragment
        ):
            raise SourceError("Link de paginação fora do endpoint permitido.")
        query = parse_qs(url.query)
        expected = {"itens": [str(self.PAGE_SIZE)], "ordem": ["ASC"], "ordenarPor": ["id"]}
        if set(query) != {*expected, "pagina"} or any(query[k] != v for k, v in expected.items()):
            raise SourceError("Parâmetros de paginação inconsistentes.")
        try:
            if len(query["pagina"]) != 1:
                raise ValueError
            page = int(query["pagina"][0])
            if page < 1:
                raise ValueError
            return page
        except ValueError:
            raise SourceError("Número de página inválido.") from None

    def fetch_current_deputies(self):
        self.pages = self.received = 0
        records, seen = [], set()
        expected_last = None
        for number in range(1, self.MAX_PAGES + 1):
            if number > 1:
                self.sleep(0.25)
            page = self._request_page(number)
            self.pages = number
            self.received += len(page.dados)
            if not page.dados or len(page.dados) > self.PAGE_SIZE:
                raise SourceError("Página vazia ou maior que o limite; coleta não publicada.")
            links = {}
            for link in page.links:
                if link.rel in links:
                    raise SourceError("Relação de paginação duplicada.")
                links[link.rel] = self._link_page(link.href)
            if links.get("self") != number:
                raise SourceError("Página retornada difere da solicitada.")
            last = links.get("last", number)
            if expected_last is None:
                expected_last = last
            if last != expected_last or last < number or last > self.MAX_PAGES:
                raise SourceError("Total de páginas alterado ou inválido; repetir coleta completa.")
            for deputy in page.dados:
                if deputy.id in seen:
                    raise SourceError("Deputado duplicado entre páginas; repetir coleta completa.")
                if deputy.uri != f"{BASE_URL}/deputados/{deputy.id}":
                    raise SourceError("Identificador e URI do deputado divergem.")
                deputy._page_number = number
                seen.add(deputy.id)
                records.append(deputy)
            if number == last:
                if "next" in links:
                    raise SourceError("Última página contém continuação inesperada.")
                return records
            if links.get("next") != number + 1 or len(page.dados) != self.PAGE_SIZE:
                raise SourceError("Paginação incompleta; coleta não publicada.")
        raise SourceError("Número máximo de páginas atingido.")
