from datetime import timedelta
from secrets import compare_digest

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dates import local_today
from app.db.session import get_db
from app.modules.analytics.integrations import integration_health
from app.modules.analytics.models import DailyMetric
from app.modules.analytics.service import PAGE_ROUTES, record

router = APIRouter(prefix="/analytics", tags=["analytics"])


class PageView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    route: str

    @field_validator("route")
    @classmethod
    def fixed_route(cls, value: str) -> str:
        if value not in PAGE_ROUTES:
            raise ValueError("Unknown page template")
        return value


def authorize(authorization: str | None = Header(default=None)) -> None:
    settings = get_settings()
    token = settings.analytics_admin_token
    if not settings.analytics_enabled or not token or not token.get_secret_value():
        raise HTTPException(404, "Not found")
    expected = f"Bearer {token.get_secret_value()}"
    if not authorization or not compare_digest(authorization.encode(), expected.encode()):
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})


@router.post("/pageviews", status_code=204)
def pageview(event: PageView, request: Request) -> Response:
    settings = get_settings()
    if not settings.analytics_enabled:
        raise HTTPException(404, "Not found")
    # Only the configured first-party frontend may submit browser metrics.
    if request.headers.get("origin") != settings.frontend_url:
        raise HTTPException(403, "Forbidden")
    if request.headers.get("dnt") != "1" and request.headers.get("sec-gpc") != "1":
        record("pageview", event.route)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.get("/summary", dependencies=[Depends(authorize)])
def summary(response: Response, days: int = 30, db: Session = Depends(get_db)) -> dict:
    if not 1 <= days <= get_settings().analytics_retention_days:
        raise HTTPException(422, "Invalid period")
    today = local_today()
    start = today - timedelta(days=days - 1)
    rows = db.scalars(select(DailyMetric).where(
        DailyMetric.day >= start, DailyMetric.day <= today,
    ).order_by(DailyMetric.day, DailyMetric.category, DailyMetric.route, DailyMetric.outcome)).all()
    response.headers["Cache-Control"] = "no-store"
    return {"start": start, "end": today, "timezone": "America/Sao_Paulo",
            "integrations": integration_health(db), "items": [
        {"day": row.day, "category": row.category, "route": row.route,
         "outcome": row.outcome, "count": row.count,
         "average_duration_ms": round(row.duration_ms / row.count, 1) if row.count else 0}
        for row in rows
    ]}
