from uuid import UUID

from pydantic import BaseModel


class PropositionSummary(BaseModel):
    id: UUID
    external_id: str
    kind: str
    number: int | None
    year: int | None
    summary: str
    presented_at: str | None
    source_url: str
    source: str
    collected_at: str


class PropositionFacets(BaseModel):
    years: list[int]
    kinds: list[str]


class PropositionPage(BaseModel):
    items: list[PropositionSummary]
    total: int
    limit: int
    offset: int
    facets: PropositionFacets


class AuthorshipResponse(BaseModel):
    parliamentarian_id: UUID | None
    author_name: str
    author_type: str | None
    author_url: str | None
    signature_order: int | None
    is_proponent: bool | None


class ProceedingsResponse(BaseModel):
    occurred_at: str | None
    sequence: int | None
    agency_url: str | None
    description: str | None
    situation: str | None
    dispatch: str | None
    rapporteur_url: str | None


class CitizenExplanationResponse(BaseModel):
    plain_summary: str
    what_changes: str | None
    affected_groups: list[str]
    practical_example: str | None
    impacts: str | None
    benefits: str | None
    cost_estimate: str | None
    analysis: str | None
    source_basis: list[str]
    method: str
    generated_at: str | None
    generation_model: str | None
    verification_model: str | None


class RelatedVotingResponse(BaseModel):
    id: UUID
    occurred_on: str | None
    title: str
    approved: bool | None
    mode: str | None
    relation_type: str


class PropositionDetail(PropositionSummary):
    detailed_summary: str | None
    full_text_url: str | None
    keywords: list[str]
    status_description: str | None
    status_agency: str | None
    status_appreciation: str | None
    status_regime: str | None
    status_at: str | None
    citizen_explanation: CitizenExplanationResponse | None
    related_votings: list[RelatedVotingResponse]
    authors: list[AuthorshipResponse]
    proceedings: list[ProceedingsResponse]
