"""Cliente sequencial para páginas públicas de pessoal, sem registrar seus dados."""

import time

import httpx


def public_html_client() -> httpx.Client:
    last_request: float | None = None

    def pace(request: httpx.Request) -> None:
        nonlocal last_request
        if last_request is not None:
            time.sleep(max(0, 1 - (time.monotonic() - last_request)))
        last_request = time.monotonic()

    return httpx.Client(
        timeout=httpx.Timeout(30, connect=10),
        follow_redirects=True,
        transport=httpx.HTTPTransport(retries=2),
        event_hooks={"request": [pace]},
        headers={"Accept": "text/html", "User-Agent": "ObservaPoder/0.1 (+https://observapoder.com.br/fontes)"},
    )
