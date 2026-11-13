"""Publica explicações cidadãs após geração e dupla validação automáticas."""

import hashlib
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import case, func, select, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.modules.proposicoes.models import (
    CitizenExplanationRun,
    Proposition,
    PropositionCitizenExplanation,
)
from app.services.citizen_drafts import (
    PROMPT_VERSION,
    CitizenExplanationAutomation,
    DraftGenerationError,
    OfficialPropositionContext,
    get_citizen_explanation_automation,
)
from app.services.citizen_validation import validate_draft

JOB = "automation.citizen_explanations"
LOCK_KEY = 2810202613
PRIORITY_KINDS = ("MPV", "PEC", "PLP", "PL")
logger = logging.getLogger("de_olho.citizen_explanations")


def now() -> datetime:
    return datetime.now(timezone.utc)


def proposition_label(row: Proposition) -> str:
    number = f" {row.number}" if row.number not in (None, 0) else ""
    year = f"/{row.year}" if row.year not in (None, 0) else ""
    return f"{row.kind}{number}{year}"


def official_context(row: Proposition) -> OfficialPropositionContext:
    return OfficialPropositionContext(
        label=proposition_label(row),
        kind=row.kind,
        summary=row.summary,
        detailed_summary=row.detailed_summary,
        status_description=row.status_description,
        keywords=row.keywords or [],
        source_url=row.source_url,
        full_text_url=row.full_text_url,
    )


def source_hash(context: OfficialPropositionContext) -> str:
    canonical = json.dumps(
        context.model_dump(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _candidate_ids(session: Session) -> list:
    latest_attempt = (
        select(
            CitizenExplanationRun.proposition_id.label("proposition_id"),
            func.max(CitizenExplanationRun.started_at).label("last_attempt_at"),
        )
        .group_by(CitizenExplanationRun.proposition_id)
        .subquery()
    )
    priority = case(
        (Proposition.kind == "MPV", 0),
        (Proposition.kind == "PEC", 1),
        (Proposition.kind == "PLP", 2),
        (Proposition.kind == "PL", 3),
        else_=4,
    )
    return list(
        session.scalars(
            select(Proposition.id)
            .outerjoin(
                PropositionCitizenExplanation,
                PropositionCitizenExplanation.proposition_id == Proposition.id,
            )
            .outerjoin(latest_attempt, latest_attempt.c.proposition_id == Proposition.id)
            .where(
                Proposition.source == "camara",
                Proposition.summary != "",
                Proposition.official_detail_collected_at.is_not(None),
            )
            .order_by(
                PropositionCitizenExplanation.id.asc().nullsfirst(),
                latest_attempt.c.last_attempt_at.asc().nullsfirst(),
                priority,
                Proposition.presented_at.desc().nullslast(),
                Proposition.id,
            )
        ).all()
    )


def _apply_published(
    explanation: PropositionCitizenExplanation,
    draft,
    *,
    context: OfficialPropositionContext,
    digest: str,
    automation: CitizenExplanationAutomation,
    validation_results: dict,
    published_at: datetime,
) -> None:
    for field in (
        "plain_summary",
        "what_changes",
        "affected_groups",
        "practical_example",
        "impacts",
        "benefits",
        "cost_estimate",
        "analysis",
    ):
        setattr(explanation, field, getattr(draft, field))
    explanation.source_basis = [context.source_url]
    explanation.method = "automated"
    explanation.review_status = "published"
    explanation.editor_name = None
    explanation.reviewed_by = None
    explanation.reviewed_at = published_at
    explanation.published_at = published_at
    explanation.source_hash = digest
    explanation.generation_model = automation.generation_model
    explanation.verification_model = automation.verification_model
    explanation.validation_results = validation_results
    explanation.generated_at = published_at


def _process_one(
    engine: Engine,
    proposition_id,
    automation: CitizenExplanationAutomation,
) -> str:
    with Session(engine) as session:
        proposition = session.get(Proposition, proposition_id)
        if proposition is None:
            return "skipped"
        context = official_context(proposition)
        digest = source_hash(context)
        current = session.scalar(
            select(PropositionCitizenExplanation).where(
                PropositionCitizenExplanation.proposition_id == proposition.id
            )
        )
        if current and current.source_hash == digest and current.review_status == "published":
            return "current"
        run = CitizenExplanationRun(
            proposition_id=proposition.id,
            status="generating",
            source_hash=digest,
            provider=automation.provider,
            generation_model=automation.generation_model,
            verification_model=automation.verification_model,
            prompt_version=PROMPT_VERSION,
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        try:
            draft = automation.generate(context)
            run.draft = draft.model_dump()
            deterministic = validate_draft(context, draft)
            run.deterministic_checks = deterministic
            if not deterministic["passed"]:
                run.status = "rejected"
                run.error_code = "deterministic_validation_failed"
                run.finished_at = now()
                session.commit()
                return "rejected"
            verification = automation.verify(context, draft)
            run.ai_verification = verification.model_dump()
            if not verification.approved:
                run.status = "rejected"
                run.error_code = "ai_verification_failed"
                run.finished_at = now()
                session.commit()
                return "rejected"
            published_at = now()
            if current is None:
                current = PropositionCitizenExplanation(
                    proposition_id=proposition.id,
                    plain_summary=draft.plain_summary,
                )
                session.add(current)
            validation_results = {
                "deterministic": deterministic,
                "ai": verification.model_dump(),
                "prompt_version": PROMPT_VERSION,
            }
            _apply_published(
                current,
                draft,
                context=context,
                digest=digest,
                automation=automation,
                validation_results=validation_results,
                published_at=published_at,
            )
            run.status = "published"
            run.finished_at = published_at
            session.commit()
            return "published"
        except DraftGenerationError as exc:
            run.status = "failed"
            run.error_code = str(exc)[:80]
            run.finished_at = now()
            session.commit()
            return "failed"
        except Exception as exc:
            logger.error("Falha inesperada na explicação cidadã: %s (%s)", proposition_id, type(exc).__name__)
            session.rollback()
            stored = session.get(CitizenExplanationRun, run.id)
            if stored:
                stored.status = "failed"
                stored.error_code = "unexpected_error"
                stored.finished_at = now()
                session.commit()
            return "failed"


def generate_citizen_explanations(
    engine: Engine,
    *,
    batch_size: int = 10,
    automation: CitizenExplanationAutomation | None = None,
) -> dict:
    automation = automation or get_citizen_explanation_automation()
    if automation is None:
        return {"status": "disabled", "processed": 0}
    counters = {"published": 0, "rejected": 0, "failed": 0, "current": 0, "skipped": 0}
    with engine.connect() as lock:
        if not lock.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}):
            return {"status": "locked", "processed": 0}
        lock.commit()
        try:
            with Session(engine) as session, session.begin():
                session.execute(
                    update(CitizenExplanationRun)
                    .where(CitizenExplanationRun.status == "generating")
                    .values(status="failed", error_code="interrupted", finished_at=now())
                )
                candidate_ids = _candidate_ids(session)
            attempts = 0
            for proposition_id in candidate_ids:
                result = _process_one(engine, proposition_id, automation)
                counters[result] += 1
                if result not in {"current", "skipped"}:
                    attempts += 1
                if attempts >= batch_size:
                    break
            return {"status": "success", "processed": attempts, **counters}
        finally:
            lock.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY})
            lock.commit()
