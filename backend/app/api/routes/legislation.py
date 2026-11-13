from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import database_session
from app.modules.proposicoes.models import (
    Authorship,
    ProceedingsEvent,
    Proposition,
    PropositionCitizenExplanation,
)
from app.modules.proposicoes.editorial import copies_official_summary
from app.modules.proposicoes.schemas import (
    AuthorshipResponse,
    CitizenExplanationResponse,
    ProceedingsResponse,
    PropositionDetail,
    PropositionFacets,
    PropositionPage,
    RelatedVotingResponse,
    PropositionSummary,
)
from app.modules.votacoes.models import Vote, Voting, VotingProposition
from app.modules.votacoes.schemas import (
    VoteResponse,
    VotingDetail,
    VotingFacets,
    VotingPage,
    VotingRelationResponse,
    VotingSummary,
)
from app.modules.parlamentares.models import Parliamentarian

router = APIRouter(tags=["legislation"])


def proposition_label(row: Proposition) -> str:
    has_number = row.number not in (None, 0)
    has_year = row.year not in (None, 0)
    if has_number and has_year:
        return f"{row.kind} {row.number}/{row.year}"
    if has_number:
        return f"{row.kind} {row.number}"
    if has_year:
        return f"{row.kind} de {row.year}"
    return row.kind


def proposition_summary(row: Proposition) -> PropositionSummary:
    return PropositionSummary(
        id=row.id,
        external_id=row.external_id,
        kind=row.kind,
        number=row.number,
        year=row.year,
        summary=row.summary,
        presented_at=row.presented_at.isoformat() if row.presented_at else None,
        source_url=row.source_url,
        source=row.source,
        collected_at=row.collected_at.isoformat(),
    )


def voting_summary(row: Voting) -> VotingSummary:
    return VotingSummary(
        id=row.id,
        external_id=row.external_id,
        occurred_on=row.occurred_on,
        description=row.description,
        object_description=row.object_description,
        approved=row.approved,
        mode=row.mode,
        source_url=row.source_url,
        source=row.source,
        collected_at=row.collected_at.isoformat(),
    )


@router.get("/propositions", response_model=list[PropositionSummary])
def list_propositions(
    source: Literal["camara", "senado"] = Query(default="camara"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    db: Session = Depends(database_session),
):
    rows = db.scalars(
        select(Proposition)
        .where(Proposition.source == source)
        .order_by(Proposition.presented_at.desc().nullslast(), Proposition.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return [proposition_summary(row) for row in rows]


@router.get("/propositions/search", response_model=PropositionPage)
def search_propositions(
    source: Literal["camara", "senado"] = Query(default="camara"),
    q: str | None = Query(default=None, max_length=200),
    year: int | None = Query(default=None, ge=1800, le=2100),
    kind: str | None = Query(default=None, min_length=1, max_length=40),
    order: Literal["newest", "oldest", "number_asc", "number_desc"] = Query(default="newest"),
    limit: int = Query(default=12, ge=1, le=48),
    offset: int = Query(default=0, ge=0, le=100000),
    db: Session = Depends(database_session),
):
    conditions = [Proposition.source == source]
    if q and q.strip():
        term = f"%{q.strip()}%"
        conditions.append(
            or_(
                Proposition.summary.ilike(term),
                Proposition.detailed_summary.ilike(term),
                Proposition.kind.ilike(term),
                Proposition.external_id.ilike(term),
                cast(Proposition.number, String).ilike(term),
            )
        )
    if year is not None:
        conditions.append(Proposition.year == year)
    if kind:
        conditions.append(Proposition.kind == kind.upper())

    ordering = {
        "newest": (Proposition.presented_at.desc().nullslast(), Proposition.id.desc()),
        "oldest": (Proposition.presented_at.asc().nullslast(), Proposition.id.asc()),
        "number_asc": (Proposition.number.asc().nullslast(), Proposition.year.desc().nullslast()),
        "number_desc": (Proposition.number.desc().nullslast(), Proposition.year.desc().nullslast()),
    }[order]
    total = db.scalar(select(func.count()).select_from(Proposition).where(*conditions)) or 0
    rows = db.scalars(
        select(Proposition).where(*conditions).order_by(*ordering).offset(offset).limit(limit)
    ).all()
    years = db.scalars(
        select(Proposition.year)
        .where(Proposition.source == source, Proposition.year.is_not(None), Proposition.year > 0)
        .distinct()
        .order_by(Proposition.year.desc())
    ).all()
    kinds = db.scalars(
        select(Proposition.kind)
        .where(Proposition.source == source)
        .distinct()
        .order_by(Proposition.kind)
    ).all()
    return PropositionPage(
        items=[proposition_summary(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
        facets=PropositionFacets(years=list(years), kinds=list(kinds)),
    )


@router.get("/votings", response_model=list[VotingSummary])
def list_votings(
    source: Literal["camara", "senado"] = Query(default="camara"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    db: Session = Depends(database_session),
):
    rows = db.scalars(
        select(Voting)
        .where(Voting.source == source)
        .order_by(Voting.occurred_on.desc().nullslast(), Voting.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return [voting_summary(row) for row in rows]


@router.get("/votings/search", response_model=VotingPage)
def search_votings(
    source: Literal["camara", "senado"] = Query(default="camara"),
    q: str | None = Query(default=None, max_length=200),
    year: int | None = Query(default=None, ge=1800, le=2100),
    result: Literal["approved", "rejected", "unknown"] | None = Query(default=None),
    mode: Literal["nominal", "unknown"] | None = Query(default=None),
    order: Literal["newest", "oldest"] = Query(default="newest"),
    limit: int = Query(default=12, ge=1, le=48),
    offset: int = Query(default=0, ge=0, le=100000),
    db: Session = Depends(database_session),
):
    conditions = [Voting.source == source]
    if q and q.strip():
        term = f"%{q.strip()}%"
        conditions.append(
            or_(
                Voting.description.ilike(term),
                Voting.object_description.ilike(term),
                Voting.external_id.ilike(term),
            )
        )
    if year is not None:
        conditions.append(func.extract("year", Voting.occurred_on) == year)
    if result == "approved":
        conditions.append(Voting.approved.is_(True))
    elif result == "rejected":
        conditions.append(Voting.approved.is_(False))
    elif result == "unknown":
        conditions.append(Voting.approved.is_(None))
    if mode == "nominal":
        conditions.append(Voting.mode == "nominal")
    elif mode == "unknown":
        conditions.append(Voting.mode.is_(None))

    ordering = (
        (Voting.occurred_on.desc().nullslast(), Voting.id.desc())
        if order == "newest"
        else (Voting.occurred_on.asc().nullslast(), Voting.id.asc())
    )
    total = db.scalar(select(func.count()).select_from(Voting).where(*conditions)) or 0
    rows = db.scalars(
        select(Voting).where(*conditions).order_by(*ordering).offset(offset).limit(limit)
    ).all()
    years = db.scalars(
        select(func.extract("year", Voting.occurred_on).cast(String))
        .where(Voting.source == source, Voting.occurred_on.is_not(None))
        .distinct()
        .order_by(func.extract("year", Voting.occurred_on).cast(String).desc())
    ).all()
    modes = db.scalars(
        select(Voting.mode)
        .where(Voting.source == source, Voting.mode.is_not(None))
        .distinct()
        .order_by(Voting.mode)
    ).all()
    return VotingPage(
        items=[voting_summary(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
        facets=VotingFacets(years=[int(value) for value in years], modes=list(modes)),
    )


@router.get("/propositions/{proposition_id}", response_model=PropositionDetail)
def get_proposition(proposition_id: UUID, db: Session = Depends(database_session)):
    row = db.get(Proposition, proposition_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Proposição não encontrada")
    authors_query = select(Authorship).where(Authorship.proposition_id == row.id)
    if row.source == "senado":
        authors_query = authors_query.where(
            Authorship.source == "senado", Authorship.source_record_id == row.source_record_id
        )
    authors = db.scalars(
        authors_query.order_by(Authorship.signature_order.nullslast(), Authorship.author_name)
    ).all()
    events = db.scalars(
        select(ProceedingsEvent)
        .where(ProceedingsEvent.proposition_id == row.id)
        .order_by(ProceedingsEvent.occurred_at, ProceedingsEvent.sequence)
    ).all()
    citizen_explanation = db.scalar(
        select(PropositionCitizenExplanation).where(
            PropositionCitizenExplanation.proposition_id == row.id,
            PropositionCitizenExplanation.review_status == "published",
            PropositionCitizenExplanation.method == "automated",
        )
    )
    if citizen_explanation and copies_official_summary(
        citizen_explanation.plain_summary,
        row.summary,
        row.detailed_summary,
    ):
        citizen_explanation = None
    related_voting_rows = db.execute(
        select(VotingProposition, Voting)
        .join(Voting, Voting.id == VotingProposition.voting_id)
        .where(VotingProposition.proposition_id == row.id)
        .order_by(Voting.occurred_on.desc().nullslast(), Voting.registered_at.desc().nullslast())
        .limit(20)
    ).all()
    relation_priority = {"object": 0, "affected": 1, "possible_object": 2}
    related_votings: dict[UUID, tuple[VotingProposition, Voting]] = {}
    for relation, voting in related_voting_rows:
        current = related_votings.get(voting.id)
        if current is None or relation_priority.get(
            relation.relation_type, 99
        ) < relation_priority.get(current[0].relation_type, 99):
            related_votings[voting.id] = (relation, voting)
    return PropositionDetail(
        id=row.id,
        external_id=row.external_id,
        kind=row.kind,
        number=row.number,
        year=row.year,
        summary=row.summary,
        presented_at=row.presented_at.isoformat() if row.presented_at else None,
        source_url=row.source_url,
        source=row.source,
        collected_at=row.collected_at.isoformat(),
        detailed_summary=row.detailed_summary,
        full_text_url=row.full_text_url,
        keywords=row.keywords or [],
        status_description=row.status_description,
        status_agency=row.status_agency,
        status_appreciation=row.status_appreciation,
        status_regime=row.status_regime,
        status_at=row.status_at.isoformat() if row.status_at else None,
        citizen_explanation=(
            CitizenExplanationResponse(
                plain_summary=citizen_explanation.plain_summary,
                what_changes=citizen_explanation.what_changes,
                affected_groups=citizen_explanation.affected_groups or [],
                practical_example=citizen_explanation.practical_example,
                impacts=citizen_explanation.impacts,
                benefits=citizen_explanation.benefits,
                cost_estimate=citizen_explanation.cost_estimate,
                analysis=citizen_explanation.analysis,
                source_basis=citizen_explanation.source_basis or [],
                method=citizen_explanation.method,
                generated_at=(
                    citizen_explanation.generated_at.isoformat()
                    if citizen_explanation.generated_at
                    else None
                ),
                generation_model=citizen_explanation.generation_model,
                verification_model=citizen_explanation.verification_model,
            )
            if citizen_explanation
            else None
        ),
        related_votings=[
            RelatedVotingResponse(
                id=voting.id,
                occurred_on=voting.occurred_on.isoformat() if voting.occurred_on else None,
                title=voting.object_description or voting.description,
                approved=voting.approved,
                mode=voting.mode,
                relation_type=relation.relation_type,
            )
            for relation, voting in related_votings.values()
        ],
        authors=[
            AuthorshipResponse(
                parliamentarian_id=(
                    a.parliamentarian_id
                    if a.source != "senado" or a.author_key.startswith("senador:")
                    else None
                ),
                author_name=a.author_name,
                author_type=a.author_type,
                author_url=a.author_url,
                signature_order=a.signature_order,
                is_proponent=a.is_proponent,
            )
            for a in authors
        ],
        proceedings=[
            ProceedingsResponse(
                occurred_at=e.occurred_at.isoformat() if e.occurred_at else None,
                sequence=e.sequence,
                agency_url=e.agency_url,
                description=e.description,
                situation=e.situation,
                dispatch=e.dispatch,
                rapporteur_url=e.rapporteur_url,
            )
            for e in events
        ],
    )


@router.get("/votings/{voting_id}", response_model=VotingDetail)
def get_voting(voting_id: UUID, db: Session = Depends(database_session)):
    row = db.get(Voting, voting_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Votação não encontrada")
    relation_rows = db.execute(
        select(VotingProposition, Proposition)
        .join(Proposition, Proposition.id == VotingProposition.proposition_id)
        .where(VotingProposition.voting_id == row.id)
        .order_by(VotingProposition.relation_type, Proposition.kind, Proposition.number)
    ).all()
    vote_query = (
        select(Vote, Parliamentarian)
        .join(Parliamentarian, Parliamentarian.id == Vote.parliamentarian_id)
        .where(Vote.voting_id == row.id)
    )
    if row.source == "senado":
        vote_query = vote_query.where(
            Vote.source == "senado",
            Parliamentarian.source == "senado",
            Vote.position != "registrado",
        )
    vote_rows = db.execute(vote_query.order_by(Parliamentarian.name)).all()
    return VotingDetail(
        id=row.id,
        external_id=row.external_id,
        occurred_on=row.occurred_on,
        description=row.description,
        object_description=row.object_description,
        approved=row.approved,
        mode=row.mode,
        source_url=row.source_url,
        source=row.source,
        collected_at=row.collected_at.isoformat(),
        propositions=[
            VotingRelationResponse(
                proposition_id=relation.proposition_id,
                relation_type=relation.relation_type,
                proposition_label=proposition_label(prop),
            )
            for relation, prop in relation_rows
        ],
        votes=[
            VoteResponse(
                parliamentarian_id=vote.parliamentarian_id,
                parliamentarian_name=person.name,
                position=vote.position,
                party_at_vote=vote.party_at_vote,
                state_at_vote=vote.state_at_vote,
            )
            for vote, person in vote_rows
        ],
    )
