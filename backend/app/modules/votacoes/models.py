import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.provenance import Provenance


class Voting(Provenance, Base):
    __tablename__ = "votings"
    __table_args__ = (UniqueConstraint("source", "external_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(100))
    occurred_on: Mapped[date | None] = mapped_column(Date, index=True)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    description: Mapped[str] = mapped_column(Text)
    object_description: Mapped[str | None] = mapped_column(Text)
    agency_url: Mapped[str | None] = mapped_column(String(1000))
    approved: Mapped[bool | None] = mapped_column(Boolean)
    # Só preencher quando documentado; lista vazia de votos não define modalidade.
    mode: Mapped[str | None] = mapped_column(String(50))


class VotingProposition(Provenance, Base):
    __tablename__ = "voting_propositions"
    voting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("votings.id"), primary_key=True)
    proposition_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("propositions.id"), primary_key=True
    )
    # objeto, objeto possível, afetada: preservar o tipo de vínculo da fonte.
    relation_type: Mapped[str] = mapped_column(String(50), primary_key=True)


class Vote(Provenance, Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("voting_id", "parliamentarian_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    voting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("votings.id"), index=True)
    parliamentarian_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("parliamentarians.id"), index=True
    )
    position: Mapped[str] = mapped_column(String(100))
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    party_at_vote: Mapped[str | None] = mapped_column(String(40))
    state_at_vote: Mapped[str | None] = mapped_column(String(2))
