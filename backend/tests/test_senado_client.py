from datetime import date

import pytest

from app.integrations.senado.client import SourceError, parse_current_senators


def test_parse_current_senators_selects_active_legislature_and_normalizes_urls():
    body = b"""
    <ListaParlamentarEmExercicio>
      <Parlamentares><Parlamentar>
        <IdentificacaoParlamentar>
          <CodigoParlamentar>123</CodigoParlamentar>
          <NomeParlamentar>Senadora Exemplo</NomeParlamentar>
          <UrlFotoParlamentar>http://senado.leg.br/foto.jpg</UrlFotoParlamentar>
          <UrlPaginaParlamentar>http://senado.leg.br/perfil/123</UrlPaginaParlamentar>
          <SiglaPartidoParlamentar>ABC</SiglaPartidoParlamentar>
          <UfParlamentar>sp</UfParlamentar>
        </IdentificacaoParlamentar>
        <Mandato>
          <PrimeiraLegislaturaDoMandato><NumeroLegislatura>56</NumeroLegislatura><DataInicio>2019-02-01</DataInicio><DataFim>2023-01-31</DataFim></PrimeiraLegislaturaDoMandato>
          <SegundaLegislaturaDoMandato><NumeroLegislatura>57</NumeroLegislatura><DataInicio>2023-02-01</DataInicio><DataFim>2027-01-31</DataFim></SegundaLegislaturaDoMandato>
        </Mandato>
      </Parlamentar></Parlamentares>
    </ListaParlamentarEmExercicio>
    """
    [senator] = parse_current_senators(body, today=date(2026, 1, 1))
    assert senator.legislature == "57"
    assert senator.state == "SP"
    assert senator.photo_url == "https://senado.leg.br/foto.jpg"


def test_parse_current_senators_rejects_invalid_contract():
    with pytest.raises(SourceError):
        parse_current_senators(b"<unexpected />")


@pytest.mark.parametrize("today", [date(2018, 1, 1), date(2031, 1, 1)])
def test_parse_rejects_mandate_without_current_legislature(today):
    body = b"""
    <ListaParlamentarEmExercicio><Parlamentares><Parlamentar>
      <IdentificacaoParlamentar>
        <CodigoParlamentar>123</CodigoParlamentar>
        <NomeParlamentar>Exemplo</NomeParlamentar>
        <UrlPaginaParlamentar>https://senado.leg.br/perfil/123</UrlPaginaParlamentar>
        <UfParlamentar>SP</UfParlamentar>
      </IdentificacaoParlamentar>
      <Mandato><PrimeiraLegislaturaDoMandato>
        <NumeroLegislatura>57</NumeroLegislatura>
        <DataInicio>2023-02-01</DataInicio><DataFim>2027-01-31</DataFim>
      </PrimeiraLegislaturaDoMandato></Mandato>
    </Parlamentar></Parlamentares></ListaParlamentarEmExercicio>
    """
    with pytest.raises(SourceError, match="legislatura vigente"):
        parse_current_senators(body, today=today)


def test_parse_uses_business_date(monkeypatch):
    from app.integrations.senado import client

    calls = []
    monkeypatch.setattr(client, "local_today", lambda: calls.append(True) or date(2026, 1, 1))
    with pytest.raises(SourceError, match="Lista vazia"):
        parse_current_senators(b"<ListaParlamentarEmExercicio />")
    assert calls == [True]
