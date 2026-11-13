from time import perf_counter

from starlette.concurrency import run_in_threadpool

from app.modules.analytics.service import record

SEARCH_KEYS = {b"search", b"q"}
FILTER_KEYS = {
    b"state", b"party", b"source", b"status", b"year", b"month",
    b"date", b"date_from", b"date_to", b"kind", b"result", b"mode",
}


class AnalyticsMiddleware:
    """Pure ASGI middleware: bounded route templates, no bodies or query values."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started = perf_counter()
        status = 500

        async def capture(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, capture)
        finally:
            route = getattr(scope.get("route"), "path", None)
            # Unmatched paths and admin/health/ingestion traffic are excluded.
            if route and route.startswith(("/api/v1/parliamentarians", "/api/v1/propositions", "/api/v1/votings")):
                await run_in_threadpool(record, "api_request", route, str(status), int((perf_counter() - started) * 1000))
                if scope["method"] == "GET" and 200 <= status < 300:
                    if route.endswith(".pdf"):
                        await run_in_threadpool(record, "download", route)
                    # Parse only parameter names; never retain their values.
                    keys = {part.split(b"=", 1)[0] for part in scope.get("query_string", b"").split(b"&")}
                    if SEARCH_KEYS.intersection(keys):
                        await run_in_threadpool(record, "search_request", route)
                    if FILTER_KEYS.intersection(keys):
                        await run_in_threadpool(record, "filter_request", route)
