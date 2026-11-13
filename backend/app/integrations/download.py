"""Bounded reads from official sources."""

from collections.abc import Iterator
from time import monotonic

import httpx


def bounded_chunks(
    response: httpx.Response, max_bytes: int, deadline: float,
) -> Iterator[bytes]:
    response.raise_for_status()
    size = 0
    for chunk in response.iter_bytes(chunk_size=65536):
        size += len(chunk)
        if size > max_bytes:
            raise ValueError("Arquivo da fonte excedeu o limite de tamanho.")
        if monotonic() > deadline:
            raise ValueError("Arquivo da fonte excedeu o prazo de download.")
        yield chunk


def download_bytes(
    client: httpx.Client, url: str, *, max_bytes: int, seconds: int = 120,
) -> bytes:
    deadline = monotonic() + seconds
    with client.stream("GET", url, follow_redirects=False) as response:
        return b"".join(bounded_chunks(response, max_bytes, deadline))
