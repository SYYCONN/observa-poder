import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.provenance import Provenance


class Parliamentarian(Provenance, Base):
    __tablename__ = "parliamentarians"
    __table_args__ = (UniqueConstraint("source", "external_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(250), index=True)
    photo_url: Mapped[str | None] = mapped_column(String(1000))
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    birth_date: Mapped[date | None] = mapped_column(Date)
    profile_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    profile_source_record_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_records.id")
    )


class Mandate(Provenance, Base):
    __tablename__ = "mandates"
    __table_args__ = (UniqueConstraint("parliamentarian_id", "source", "legislature_external_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    parliamentarian_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parliamentarians.id"), index=True
    )
    legislature_external_id: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2), index=True)
    party: Mapped[str | None] = mapped_column(String(40))
    party_source_url: Mapped[str | None] = mapped_column(String(1000))
    # Não preencher com datas da legislatura: não provam início/fim individual.
    started_on: Mapped[date | None] = mapped_column(Date)
    ended_on: Mapped[date | None] = mapped_column(Date)


class MandateObservation(Base):
    __tablename__ = "mandate_observations"
    __table_args__ = (UniqueConstraint("mandate_id", "run_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    mandate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mandates.id"), index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("import_runs.id"))
    source_record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("source_records.id"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(2))
    party: Mapped[str | None] = mapped_column(String(40))
    party_source_url: Mapped[str | None] = mapped_column(String(1000))


class ElectionResult(Provenance, Base):
    """Resultado eleitoral nominal associado a um parlamentar por fonte e ano."""

    __tablename__ = "election_results"
    __table_args__ = (UniqueConstraint("parliamentarian_id", "source", "election_year", "office"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    parliamentarian_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parliamentarians.id"), index=True
    )
    election_year: Mapped[int] = mapped_column(index=True)
    election_round: Mapped[int] = mapped_column()
    office: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(2))
    candidate_number: Mapped[str | None] = mapped_column(String(20))
    candidate_name: Mapped[str] = mapped_column(String(250))
    party: Mapped[str | None] = mapped_column(String(40))
    votes: Mapped[int] = mapped_column()
    valid_votes: Mapped[int | None] = mapped_column()
    election_status: Mapped[str | None] = mapped_column(String(120))
