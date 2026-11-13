import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.provenance import Provenance


class ParliamentaryExpense(Provenance, Base):
    """Despesa publicada na Cota para o Exercício da Atividade Parlamentar."""

    __tablename__ = "parliamentary_expenses"
    __table_args__ = (UniqueConstraint("source", "external_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(100))
    parliamentarian_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("parliamentarians.id"), index=True
    )
    occurred_on: Mapped[date | None] = mapped_column(Date, index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    month: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(250))
    category_detail: Mapped[str | None] = mapped_column(Text)
    supplier_name: Mapped[str | None] = mapped_column(String(500))
    document_number: Mapped[str | None] = mapped_column(String(100))
    document_type: Mapped[str | None] = mapped_column(String(50))
    amount_document: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    amount_glossed: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    amount_net: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    reimbursement: Mapped[str | None] = mapped_column(String(100))
    source_document_url: Mapped[str | None] = mapped_column(String(1000))


class ParliamentaryRemuneration(Provenance, Base):
    """Folha mensal publicada para um parlamentar pela Câmara."""

    __tablename__ = "parliamentary_remunerations"
    __table_args__ = (
        UniqueConstraint("parliamentarian_id", "source", "year", "month", "payroll_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    parliamentarian_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parliamentarians.id"), index=True
    )
    year: Mapped[int] = mapped_column(Integer, index=True)
    month: Mapped[int] = mapped_column(Integer)
    payroll_type: Mapped[str] = mapped_column(String(80), default="folha_normal")
    fixed_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    net_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    source_document_url: Mapped[str] = mapped_column(String(1000))


class ParliamentaryStaffSummary(Provenance, Base):
    """Resumo mensal da equipe em exercício no gabinete parlamentar."""

    __tablename__ = "parliamentary_staff_summaries"
    __table_args__ = (
        UniqueConstraint("parliamentarian_id", "source", "year", "month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    parliamentarian_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parliamentarians.id"), index=True
    )
    year: Mapped[int] = mapped_column(Integer, index=True)
    month: Mapped[int] = mapped_column(Integer)
    staff_count: Mapped[int] = mapped_column(Integer)
    source_query_url: Mapped[str] = mapped_column(String(1000))


class ParliamentaryStaffMember(Provenance, Base):
    """Servidor publicado na equipe em exercício de um gabinete."""

    __tablename__ = "parliamentary_staff_members"
    __table_args__ = (
        UniqueConstraint("parliamentarian_id", "source", "external_id", "year", "month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(120), index=True)
    parliamentarian_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parliamentarians.id"), index=True
    )
    year: Mapped[int] = mapped_column(Integer, index=True)
    month: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(250))
    category: Mapped[str | None] = mapped_column(String(150))
    area_of_work: Mapped[str | None] = mapped_column(String(250))
    job_title: Mapped[str | None] = mapped_column(String(250))
    level: Mapped[str | None] = mapped_column(String(50))
    gross_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    net_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    allowances_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    source_query_url: Mapped[str] = mapped_column(String(1000))
    source_remuneration_url: Mapped[str | None] = mapped_column(String(1000))
    payroll_type: Mapped[str | None] = mapped_column(String(100))
    exercise_date: Mapped[str | None] = mapped_column(String(20))


class ParliamentaryAmendment(Provenance, Base):
    """Registro individual de emenda pública associada ao parlamentar."""

    __tablename__ = "parliamentary_amendments"
    __table_args__ = (UniqueConstraint("parliamentarian_id", "source", "external_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(100), index=True)
    parliamentarian_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parliamentarians.id"), index=True
    )
    year: Mapped[int] = mapped_column(Integer, index=True)
    amendment_type: Mapped[str | None] = mapped_column(String(250))
    locality: Mapped[str | None] = mapped_column(String(500))
    municipality: Mapped[str | None] = mapped_column(String(250))
    state: Mapped[str | None] = mapped_column(String(2))
    function_name: Mapped[str | None] = mapped_column(String(250))
    subfunction_name: Mapped[str | None] = mapped_column(String(250))
    program_name: Mapped[str | None] = mapped_column(Text)
    action_name: Mapped[str | None] = mapped_column(Text)
    plan_name: Mapped[str | None] = mapped_column(Text)
    committed_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    liquidated_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    paid_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))


class ParliamentaryAmendmentSummary(Provenance, Base):
    """Valores agregados das emendas de autoria por parlamentar e exercício."""

    __tablename__ = "parliamentary_amendment_summaries"
    __table_args__ = (UniqueConstraint("parliamentarian_id", "source", "year"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    parliamentarian_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parliamentarians.id"), index=True
    )
    year: Mapped[int] = mapped_column(Integer, index=True)
    amendment_count: Mapped[int] = mapped_column(Integer)
    committed_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    liquidated_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    paid_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    source_query_url: Mapped[str] = mapped_column(String(1000))
