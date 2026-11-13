import httpx
import pytest

from app.integrations.download import download_bytes


def test_download_rejects_body_larger_than_limit():
    with httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, content=b"12345")
    )) as client:
        with pytest.raises(ValueError, match="limite de tamanho"):
            download_bytes(client, "https://example.test/source", max_bytes=4)


def test_download_does_not_follow_redirect_even_if_client_would():
    seen = []

    def handler(request):
        seen.append(request.url.host)
        return httpx.Response(302, headers={"Location": "https://other.test/source"})

    with httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        with pytest.raises(httpx.HTTPStatusError):
            download_bytes(client, "https://example.test/source", max_bytes=4)
    assert seen == ["example.test"]
