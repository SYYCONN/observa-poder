"""Bounded, per-process abuse controls for the public API.

The transport peer is authoritative. Uvicorn must not trust arbitrary forwarded headers.
Distributed limits and connection/bandwidth protection belong at the edge/proxy.
"""

import asyncio
import logging
import math
from collections import OrderedDict
from time import monotonic
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings

logger = logging.getLogger("app.requests")


class TokenBuckets:
    def __init__(self, per_minute: int, burst: int, max_clients: int):
        self.rate = per_minute / 60
        self.burst = burst
        self.max_clients = max_clients
        self.clients: OrderedDict[str, tuple[float, float]] = OrderedDict()

    def consume(self, client: str, now: float) -> int:
        # Idle buckets have fully refilled and can be discarded without resetting debt.
        idle_seconds = self.burst / self.rate
        while self.clients:
            _, (_, last_seen) = next(iter(self.clients.items()))
            if now - last_seen < idle_seconds:
                break
            self.clients.popitem(last=False)
        if client not in self.clients and len(self.clients) >= self.max_clients:
            return max(1, math.ceil(idle_seconds))
        tokens, last_seen = self.clients.pop(client, (float(self.burst), now))
        tokens = min(self.burst, tokens + (now - last_seen) * self.rate)
        retry_after = max(1, math.ceil((1 - tokens) / self.rate)) if tokens < 1 else 0
        self.clients[client] = (tokens if retry_after else tokens - 1, now)
        return retry_after


class SecurityMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings):
        self.app = app
        logger.setLevel(logging.INFO)
        if not logger.hasHandlers():
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
            )
            logger.addHandler(handler)
        self.production = settings.app_env == "production"
        self.analytics_enabled = settings.analytics_enabled
        self.requests = TokenBuckets(
            settings.rate_limit_per_minute,
            settings.rate_limit_burst,
            settings.rate_limit_max_clients,
        )
        self.exports = TokenBuckets(
            settings.export_limit_per_minute,
            settings.export_limit_burst,
            settings.rate_limit_max_clients,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid4().hex
        started = monotonic()
        status = 500
        response_started = False

        async def secure_send(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                status = message["status"]
                response_started = True
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "no-referrer"
                headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
                if scope["path"].startswith("/api/"):
                    headers["Content-Security-Policy"] = (
                        "default-src 'none'; frame-ancestors 'none'"
                    )
                if status >= 400:
                    headers["Cache-Control"] = "no-store"
                if self.production:
                    headers["Strict-Transport-Security"] = "max-age=31536000"
            await send(message)

        async def reject(code: int, detail: str, headers: dict | None = None) -> None:
            await JSONResponse({"detail": detail}, status_code=code, headers=headers)(
                scope,
                receive,
                secure_send,
            )

        async def forward_bounded_body(max_bytes: int, timeout_seconds: int) -> None:
            body = bytearray()
            try:
                async with asyncio.timeout(timeout_seconds):
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return
                        chunk = message.get("body", b"")
                        if len(body) + len(chunk) > max_bytes:
                            await reject(413, "Request body too large")
                            return
                        body.extend(chunk)
                        if not message.get("more_body", False):
                            break
            except TimeoutError:
                await reject(408, "Request body timeout")
                return

            delivered = False

            async def bounded_receive() -> Message:
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await self.app(scope, bounded_receive, secure_send)

        try:
            peer = scope.get("client")
            retry = self.requests.consume(peer[0] if peer else "unknown", started)
            if retry:
                await reject(429, "Too many requests", {"Retry-After": str(retry)})
            elif len(scope.get("raw_path", b"")) + len(scope.get("query_string", b"")) > 8192:
                await reject(414, "Request URI too long")
            elif (
                scope["method"] == "POST"
                and self.analytics_enabled
                and scope["path"] == "/api/v1/analytics/pageviews"
            ):
                await forward_bounded_body(4096, 5)
            elif scope["method"] not in {"GET", "HEAD", "OPTIONS"}:
                await reject(405, "Method not allowed", {"Allow": "GET, HEAD, OPTIONS"})
            elif scope["path"].endswith((".pdf", ".csv")) and (
                retry := self.exports.consume(peer[0] if peer else "unknown", started)
            ):
                await reject(429, "Too many exports", {"Retry-After": str(retry)})
            else:
                await self.app(scope, receive, secure_send)
        except Exception as exc:
            # Never log exception values, query strings, headers, or bodies (may contain secrets).
            logger.error("request_error id=%s type=%s", request_id, type(exc).__name__)
            if response_started:
                # Abort the response without passing sensitive exception values to Uvicorn.
                raise RuntimeError("Response interrupted") from None
            await reject(500, "Internal server error")
        finally:
            route = scope.get("route")
            logger.info(
                "request id=%s route=%s status=%s duration_ms=%s",
                request_id,
                getattr(route, "path", "unmatched"),
                status,
                round((monotonic() - started) * 1000),
            )
