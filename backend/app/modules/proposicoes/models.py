import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.provenance import Provenance


class Proposition(Provenance, Base):
    __tablename__ = "propositions"
    __table_args__ = (UniqueConstraint("source", "external_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(40))
    number: Mapped[int | None] = mapped_column(Integer)
    year: Mapped[int | None] = mapped_column(Integer, index=True)
    summary: Mapped[str] = mapped_column(Text)
    detailed_summary: Mapped[str | None] = mapped_column(Text)
    full_text_url: Mapped[str | None] = mapped_column(String(1000))
    keywords: Mapped[list[str] | None] = mapped_column(JSON)
    status_description: Mapped[str | None] = mapped_column(Text)
    status_agency: Mapped[str | None] = mapped_column(String(100))
    status_appreciation: Mapped[str | None] = mapped_column(String(250))
    status_regime: Mapped[str | None] = mapped_column(String(250))
    status_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    official_detail_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    presented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PropositionCitizenExplanation(Base):
    """Explicação vigente, publicada somente pela esteira automática."""

    __tablename__ = "proposition_citizen_explanations"
    __table_args__ = (
        UniqueConstraint("proposition_id"),
        CheckConstraint(
            "review_status IN ('draft', 'reviewed', 'published')",
            name="citizen_explanation_review_status",
        ),
        CheckConstraint(
            "method IN ('editorial', 'assisted', 'automated')",
            name="citizen_explanation_method",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    proposition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("propositions.id", ondelete="CASCADE"), index=True
    )
    plain_summary: Mapped[str] = mapped_column(Text)
    what_changes: Mapped[str | None] = mapped_column(Text)
    affected_groups: Mapped[list[str] | None] = mapped_column(JSON)
    practical_example: Mapped[str | None] = mapped_column(Text)
    impacts: Mapped[str | None] = mapped_column(Text)
    benefits: Mapped[str | None] = mapped_column(Text)
    cost_estimate: Mapped[str | None] = mapped_column(Text)
    analysis: Mapped[str | None] = mapped_column(Text)
    source_basis: Mapped[list[str] | None] = mapped_column(JSON)
    method: Mapped[str] = mapped_column(String(20), default="editorial")
    review_status: Mapped[str] = mapped_column(String(20), default="draft")
    editor_name: Mapped[str | None] = mapped_column(String(120))
    reviewed_by: Mapped[str | None] = mapped_column(String(120))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    generation_model: Mapped[str | None] = mapped_column(String(200))
    verification_model: Mapped[str | None] = mapped_column(String(200))
    validation_results: Mapped[dict | None] = mapped_column(JSON)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CitizenExplanationRun(Base):
    """Registro imutável de cada tentativa da automação cidadã."""

    __tablename__ = "citizen_explanation_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('generating', 'published', 'rejected', 'failed')",
            name="citizen_explanation_run_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    proposition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("propositions.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="generating", index=True)
    source_hash: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    generation_model: Mapped[str] = mapped_column(String(200))
    verification_model: Mapped[str] = mapped_column(String(200))
    prompt_version: Mapped[str] = mapped_column(String(40))
    draft: Mapped[dict | None] = mapped_column(JSON)
    deterministic_checks: Mapped[dict | None] = mapped_column(JSON)
    ai_verification: Mapped[dict | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(80))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Authorship(Provenance, Base):
    __tablename__ = "authorships"
    __table_args__ = (UniqueConstraint("proposition_id", "source", "author_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    proposition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("propositions.id"), index=True)
    # URI oficial ou chave local documentada; não consolidar homônimos entre projetos.
    author_key: Mapped[str] = mapped_column(String(500))
    author_name: Mapped[str] = mapped_column(String(500))
    author_type: Mapped[str | None] = mapped_column(String(100))
    author_url: Mapped[str | None] = mapped_column(String(1000))
    parliamentarian_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("parliamentarians.id"))
    signature_order: Mapped[int | None] = mapped_column(Integer)
    is_proponent: Mapped[bool | None] = mapped_column(Boolean)


class ProceedingsEvent(Provenance, Base):
    __tablename__ = "proceedings_events"
    __table_args__ = (UniqueConstraint("proposition_id", "source", "external_key"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    proposition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("propositions.id"), index=True)
    external_key: Mapped[str] = mapped_column(String(100))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sequence: Mapped[int | None] = mapped_column(Integer)
    agency_url: Mapped[str | None] = mapped_column(String(1000))
    description: Mapped[str | None] = mapped_column(Text)
    situation: Mapped[str | None] = mapped_column(Text)
    dispatch: Mapped[str | None] = mapped_column(Text)
    rapporteur_url: Mapped[str | None] = mapped_column(String(1000))
