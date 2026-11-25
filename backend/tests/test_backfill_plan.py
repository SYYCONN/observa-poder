import gzip
from datetime import date

import httpx
import pytest

from app.jobs import backfill_legislation as job


@pytest.mark.parametrize("identifier", ["../secret", "https://other.example", "1?token=x", "0", "1/2"])
def test_only_official_identifier_formats_are_accepted(identifier):
    with pytest.raises(ValueError):
        job.plan("camara", proposition_ids=[identifier])


def test_periods_are_bounded_and_senate_votes_require_year():
    with pytest.raises(ValueError):
        job.plan("camara", start=date(2026, 1, 1), end=date(2026, 3, 1))
    with pytest.raises(ValueError):
        job.plan("senado", voting_ids=["123"])
    with pytest.raises(ValueError):
        job.plan("camara", year=2026, discover_votes=True)
    with pytest.raises(ValueError):
        job.plan("senado", year=2026, discover_votes=True, start=date(2026,12,31), end=date(2027,1,1))


def test_decoded_response_is_not_decompressed_twice():
    data = gzip.compress(b'{"dados": []}')
    with job.SourceClient(transport=httpx.MockTransport(lambda r: httpx.Response(
        200, content=data, headers={"Content-Encoding": "gzip"}))) as client:
        assert client.get("https://dadosabertos.camara.leg.br/api/v2/votacoes").json() == {"dados": []}


def test_discovery_resumes_pages_without_following_external_next_url(tmp_path):
    request = job.plan("camara", start=date(2026, 11, 18), end=date(2026, 11, 18))
    state = dict(plan=request, targets={}, pages={}, discovery_done=False)
    calls = []
    def page(r):
        calls.append(str(r.url))
        if r.url.path.endswith("/votacoes"):
            return httpx.Response(200, json={"dados": [], "links": []})
        number = int(r.url.params["pagina"])
        return httpx.Response(200, json={"dados": [{"id": number}], "links": [
            {"rel": "next", "href": "http://169.254.169.254/"}] if number == 1 else []})
    with httpx.Client(transport=httpx.MockTransport(page)) as client:
        job.discover(client, state, 1, {}, tmp_path / "state.json")
        assert not state["discovery_done"]
        assert state["pages"]["proposition"] == 2
        job.discover(client, state, 1, {})
    assert state["discovery_done"]
    assert len(state["targets"]) == 2
    assert all(url.startswith(job.camara.BASE) for url in calls)
