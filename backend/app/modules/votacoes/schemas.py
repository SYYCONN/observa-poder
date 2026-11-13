from datetime import date
from uuid import UUID

from pydantic import BaseModel


class VotingSummary(BaseModel):
    id: UUID
    external_id: str
    occurred_on: date | None
    description: str
    object_description: str | None
    approved: bool | None
    mode: str | None
    source_url: str
    source: str
    collected_at: str


class VotingFacets(BaseModel):
    years: list[int]
    modes: list[str]


class VotingPage(BaseModel):
    items: list[VotingSummary]
    total: int
    limit: int
    offset: int
    facets: VotingFacets


class VotingRelationResponse(BaseModel):
    proposition_id: UUID
    relation_type: str
    proposition_label: str


class VoteResponse(BaseModel):
    parliamentarian_id: UUID
    parliamentarian_name: str
    position: str
    party_at_vote: str | None
    state_at_vote: str | None


class VotingDetail(VotingSummary):
    propositions: list[VotingRelationResponse]
    votes: list[VoteResponse]
