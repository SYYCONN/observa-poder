"""Monitor técnico somente leitura da automação de explicações cidadãs."""

from secrets import compare_digest
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import database_session
from app.core.config import get_settings
from app.modules.proposicoes.models import (
    CitizenExplanationRun,
    Proposition,
    PropositionCitizenExplanation,
)


def authorize_content(authorization: str | None = Header(default=None)) -> None:
    token = get_settings().content_admin_token
    if not token or not token.get_secret_value():
        raise HTTPException(404, "Not found")
    expected = f"Bearer {token.get_secret_value()}"
    if not authorization or not compare_digest(authorization.encode(), expected.encode()):
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})


router = APIRouter(
    prefix="/content-admin/citizen-explanations",
    tags=["content-automation"],
    dependencies=[Depends(authorize_content)],
)


def proposition_label(row: Proposition) -> str:
    number = f" {row.number}" if row.number not in (None, 0) else ""
    year = f"/{row.year}" if row.year not in (None, 0) else ""
    return f"{row.kind}{number}{year}"


def run_payload(run: CitizenExplanationRun) -> dict:
    return {
        "id": run.id,
        "status": run.status,
        "source_hash": run.source_hash,
        "provider": run.provider,
        "generation_model": run.generation_model,
        "verification_model": run.verification_model,
        "prompt_version": run.prompt_version,
        "deterministic_checks": run.deterministic_checks,
        "ai_verification": run.ai_verification,
        "error_code": run.error_code,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


@router.get("")
def list_automation_runs(
    response: Response,
    status: Literal["generating", "published", "rejected", "failed", "all"] = Query(default="all"),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    db: Session = Depends(database_session),
):
    conditions = [] if status == "all" else [CitizenExplanationRun.status == status]
    total = db.scalar(select(func.count(CitizenExplanationRun.id)).where(*conditions)) or 0
    rows = db.execute(
        select(CitizenExplanationRun, Proposition)
        .join(Proposition, Proposition.id == CitizenExplanationRun.proposition_id)
        .where(*conditions)
        .order_by(CitizenExplanationRun.started_at.desc(), CitizenExplanationRun.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    counts = dict(
        db.execute(
            select(CitizenExplanationRun.status, func.count(CitizenExplanationRun.id)).group_by(
                CitizenExplanationRun.status
            )
        ).all()
    )
    response.headers["Cache-Control"] = "no-store"
    return {
        "items": [
            {
                **run_payload(run),
                "proposition_id": proposition.id,
                "label": proposition_label(proposition),
                "summary": proposition.summary,
            }
            for run, proposition in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
        "counts": {
            "generating": counts.get("generating", 0),
            "published": counts.get("published", 0),
            "rejected": counts.get("rejected", 0),
            "failed": counts.get("failed", 0),
        },
    }


@router.get("/{proposition_id}")
def get_automation_detail(
    proposition_id: UUID,
    response: Response,
    db: Session = Depends(database_session),
):
    proposition = db.get(Proposition, proposition_id)
    if proposition is None:
        raise HTTPException(404, "Proposição não encontrada")
    explanation = db.scalar(
        select(PropositionCitizenExplanation).where(
            PropositionCitizenExplanation.proposition_id == proposition_id
        )
    )
    runs = db.scalars(
        select(CitizenExplanationRun)
        .where(CitizenExplanationRun.proposition_id == proposition_id)
        .order_by(CitizenExplanationRun.started_at.desc(), CitizenExplanationRun.id.desc())
        .limit(20)
    ).all()
    response.headers["Cache-Control"] = "no-store"
    return {
        "id": proposition.id,
        "label": proposition_label(proposition),
        "summary": proposition.summary,
        "source_url": proposition.source_url,
        "published": (
            {
                "plain_summary": explanation.plain_summary,
                "source_hash": explanation.source_hash,
                "generated_at": (
                    explanation.generated_at.isoformat() if explanation.generated_at else None
                ),
                "generation_model": explanation.generation_model,
                "verification_model": explanation.verification_model,
                "validation_results": explanation.validation_results,
            }
            if explanation and explanation.review_status == "published"
            else None
        ),
        "runs": [run_payload(run) for run in runs],
    }
