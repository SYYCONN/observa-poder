from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import router
from app.core.config import get_settings
from app.core.security import SecurityMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="De Olho na Política API",
        version="0.1.0",
        docs_url="/docs" if settings.app_env == "development" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.app_env == "development" else None,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(SecurityMiddleware, settings=settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_methods=["GET", "POST"] if settings.analytics_enabled else ["GET"],
        allow_headers=["Accept", "Content-Type", "Authorization"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )
    if settings.analytics_enabled:
        from app.modules.analytics.middleware import AnalyticsMiddleware

        app.add_middleware(AnalyticsMiddleware)
    app.include_router(router, prefix="/api/v1")
    return app
