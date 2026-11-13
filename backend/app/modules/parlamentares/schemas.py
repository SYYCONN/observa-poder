from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.financas.schemas import FinancialSummaryResponse


class MandateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    legislature: str
    state: str
    party: str | None
    started_on: str | None
    ended_on: str | None
    source_url: str
    collected_at: str


class ParliamentarianSummary(BaseModel):
    id: UUID
    external_id: str
    name: str
    photo_url: str | None
    state: str | None
    party: str | None
    legislature: str | None
    source_url: str
    source: str
    collected_at: str
    is_current: bool


class ParliamentarianPage(BaseModel):
    items: list[ParliamentarianSummary]
    total: int
    limit: int
    offset: int


class AuthoredPropositionResponse(BaseModel):
    id: UUID
    label: str
    summary: str
    presented_at: str | None
    source_url: str


class AuthoredPropositionPage(BaseModel):
    items: list[AuthoredPropositionResponse]
    total: int
    limit: int
    offset: int


class VoteRecordResponse(BaseModel):
    voting_id: UUID
    occurred_on: str | None
    description: str
    object_description: str | None
    position: str
    party_at_vote: str | None
    state_at_vote: str | None
    source_url: str


class VoteRecordPage(BaseModel):
    items: list[VoteRecordResponse]
    total: int
    limit: int
    offset: int


class ParliamentarianDetail(ParliamentarianSummary):
    birth_date: str | None
    profile_source_url: str | None
    mandates: list[MandateResponse]
    election_votes: int | None
    election_year: int | None
    election_status: str | None
    election_source_url: str | None
    mandate_started_on: str | None
    mandate_ended_on: str | None
    authored_propositions: list[AuthoredPropositionResponse]
    authored_propositions_total: int
    vote_records: list[VoteRecordResponse]
    votes_total: int
    votes_by_position: dict[str, int]
    financial_summary: FinancialSummaryResponse
