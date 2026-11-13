import csv
import io
import re
from datetime import date
from uuid import UUID
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import database_session
from app.integrations.camara.remuneration import subsidy_reference
from app.modules.proposicoes.models import Authorship, Proposition
from app.modules.financas.models import (
    ParliamentaryAmendment,
    ParliamentaryAmendmentSummary,
    ParliamentaryExpense,
    ParliamentaryRemuneration,
    ParliamentaryStaffMember,
    ParliamentaryStaffSummary,
)
from app.modules.financas.schemas import (
    FinancialSummaryResponse,
    ParliamentaryExpensePage,
    ParliamentaryExpenseResponse,
    ParliamentaryStaffMemberResponse,
    ParliamentaryStaffPage,
)
from app.modules.parlamentares.models import ElectionResult, Mandate, Parliamentarian
from app.modules.votacoes.models import Vote, Voting
from app.services.amendments_pdf import build_amendments_pdf
from app.services.staff_pdf import build_staff_pdf
from app.modules.parlamentares.schemas import (
    AuthoredPropositionResponse,
    AuthoredPropositionPage,
    MandateResponse,
    ParliamentarianPage,
    ParliamentarianDetail,
    ParliamentarianSummary,
    VoteRecordResponse,
    VoteRecordPage,
)

router = APIRouter(prefix="/parliamentarians", tags=["parliamentarians"])


def format_brazilian_amount(value) -> str:
    if value is None:
        return ""
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def proposition_label(proposition: Proposition) -> str:
    has_number = proposition.number not in (None, 0)
    has_year = proposition.year not in (None, 0)
    if has_number and has_year:
        return f"{proposition.kind} {proposition.number}/{proposition.year}"
    if has_number:
        return f"{proposition.kind} {proposition.number}"
    if has_year:
        return f"{proposition.kind} de {proposition.year}"
    return proposition.kind


def summary(person: Parliamentarian, mandate: Mandate | None) -> ParliamentarianSummary:
    return ParliamentarianSummary(
        id=person.id,
        external_id=person.external_id,
        name=person.name,
        photo_url=person.photo_url,
        state=mandate.state if mandate else None,
        party=mandate.party if mandate else None,
        source=person.source,
        legislature=mandate.legislature_external_id if mandate else None,
        source_url=person.source_url,
        collected_at=person.collected_at.isoformat(),
        is_current=person.is_current,
    )


@router.get("", response_model=ParliamentarianPage)
def list_parliamentarians(
    search: str | None = Query(default=None, min_length=1, max_length=100),
    state: str | None = Query(default=None, min_length=2, max_length=2, pattern="^[A-Za-z]{2}$"),
    party: str | None = Query(default=None, max_length=40),
    source: Literal["camara", "senado"] = Query(default="camara"),
    status: Literal["current", "historical", "all"] = Query(default="current"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
    db: Session = Depends(database_session),
):
    latest = (
        select(Mandate.parliamentarian_id, Mandate.id)
        .distinct(Mandate.parliamentarian_id)
        .order_by(
            Mandate.parliamentarian_id, Mandate.legislature_external_id.desc(), Mandate.id.desc()
        )
        .subquery()
    )
    query = (
        select(Parliamentarian, Mandate)
        .join(latest, latest.c.parliamentarian_id == Parliamentarian.id, isouter=True)
        .join(Mandate, Mandate.id == latest.c.id, isouter=True)
        .where(Parliamentarian.source == source)
    )
    if status == "current":
        query = query.where(Parliamentarian.is_current.is_(True))
    elif status == "historical":
        query = query.where(Parliamentarian.is_current.is_(False))
    if search:
        query = query.where(
            or_(Parliamentarian.name.ilike(f"%{search}%"), Parliamentarian.external_id == search)
        )
    if state:
        query = query.where(Mandate.state == state.upper())
    if party:
        query = query.where(Mandate.party == party.upper())
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = [
        summary(person, mandate)
        for person, mandate in db.execute(
            query.order_by(Parliamentarian.name, Parliamentarian.id).offset(offset).limit(limit)
        )
    ]
    return ParliamentarianPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/parties", response_model=list[str])
def list_parties(
    source: Literal["camara", "senado"] = Query(default="camara"),
    db: Session = Depends(database_session),
):
    rows = db.execute(
        select(Mandate.party)
        .join(Parliamentarian, Parliamentarian.id == Mandate.parliamentarian_id)
        .where(Parliamentarian.source == source, Mandate.party.is_not(None))
        .distinct()
        .order_by(Mandate.party)
    ).all()
    return [party for (party,) in rows if party]


@router.get("/{person_id}/financial-expenses", response_model=ParliamentaryExpensePage)
def list_financial_expenses(
    person_id: UUID,
    year: int | None = Query(default=None, ge=2000, le=2100),
    date_filter: date | None = Query(default=None, alias="date"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=100000),
    db: Session = Depends(database_session),
):
    person = db.get(Parliamentarian, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Parlamentar não encontrado")
    filters = [
        ParliamentaryExpense.parliamentarian_id == person_id,
        ParliamentaryExpense.source == "camara",
    ]
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=400, detail="A data inicial deve ser anterior à data final."
        )

    selected_year = year
    if month:
        selected_year = int(month[:4])
        month_number = int(month[5:])
        filters.extend(
            [
                ParliamentaryExpense.year == selected_year,
                ParliamentaryExpense.month == month_number,
            ]
        )
    elif date_filter:
        selected_year = date_filter.year
        filters.append(ParliamentaryExpense.occurred_on == date_filter)
    elif date_from or date_to:
        selected_year = (
            date_from.year if date_from and date_to and date_from.year == date_to.year else None
        )
        if date_from:
            filters.append(ParliamentaryExpense.occurred_on >= date_from)
        if date_to:
            filters.append(ParliamentaryExpense.occurred_on <= date_to)
    elif selected_year is not None:
        filters.append(ParliamentaryExpense.year == selected_year)
    else:
        selected_year = db.scalar(select(func.max(ParliamentaryExpense.year)).where(*filters))
    query = select(ParliamentaryExpense).where(*filters)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(
            ParliamentaryExpense.occurred_on.desc().nullslast(),
            ParliamentaryExpense.id,
        )
        .offset(offset)
        .limit(limit)
    ).all()
    return ParliamentaryExpensePage(
        items=[
            ParliamentaryExpenseResponse(
                id=str(row.id),
                external_id=row.external_id,
                year=row.year,
                occurred_on=row.occurred_on.isoformat() if row.occurred_on else None,
                month=row.month,
                category=row.category,
                category_detail=row.category_detail,
                supplier_name=row.supplier_name,
                document_number=row.document_number,
                document_type=row.document_type,
                amount_document=row.amount_document,
                amount_glossed=row.amount_glossed,
                amount_net=row.amount_net,
                reimbursement=row.reimbursement,
                source_document_url=row.source_document_url,
                source=row.source,
                source_url=row.source_url,
                collected_at=row.collected_at.isoformat(),
                source_record_id=str(row.source_record_id),
            )
            for row in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
        year=selected_year,
    )


@router.get("/{person_id}/staff", response_model=ParliamentaryStaffPage)
def list_parliamentarian_staff(
    person_id: UUID,
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=100000),
    db: Session = Depends(database_session),
):
    person = db.get(Parliamentarian, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Parlamentar não encontrado")
    if (year is None) != (month is None):
        raise HTTPException(status_code=400, detail="Informe ano e mês da equipe em conjunto.")

    selected_year, selected_month = year, month
    staff_summary = None
    if selected_year is None:
        staff_summary = db.scalar(
            select(ParliamentaryStaffSummary)
            .where(
                ParliamentaryStaffSummary.parliamentarian_id == person_id,
                ParliamentaryStaffSummary.source == "camara",
            )
            .order_by(
                ParliamentaryStaffSummary.year.desc(),
                ParliamentaryStaffSummary.month.desc(),
            )
            .limit(1)
        )
        if staff_summary:
            selected_year, selected_month = staff_summary.year, staff_summary.month
    else:
        staff_summary = db.scalar(
            select(ParliamentaryStaffSummary).where(
                ParliamentaryStaffSummary.parliamentarian_id == person_id,
                ParliamentaryStaffSummary.source == "camara",
                ParliamentaryStaffSummary.year == selected_year,
                ParliamentaryStaffSummary.month == selected_month,
            )
        )

    if selected_year is None or selected_month is None:
        return ParliamentaryStaffPage(
            items=[], total=0, limit=limit, offset=offset, year=None, month=None
        )

    filters = [
        ParliamentaryStaffMember.parliamentarian_id == person_id,
        ParliamentaryStaffMember.source == "camara",
        ParliamentaryStaffMember.year == selected_year,
        ParliamentaryStaffMember.month == selected_month,
    ]
    query = select(ParliamentaryStaffMember).where(*filters)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    members = db.scalars(
        query.order_by(ParliamentaryStaffMember.name).offset(offset).limit(limit)
    ).all()
    return ParliamentaryStaffPage(
        items=[
            ParliamentaryStaffMemberResponse(
                id=str(member.id),
                external_id=member.external_id,
                name=member.name,
                category=member.category,
                area_of_work=member.area_of_work,
                job_title=member.job_title,
                level=member.level,
                gross_amount=member.gross_amount,
                net_amount=member.net_amount,
                allowances_amount=member.allowances_amount,
                source_query_url=member.source_query_url,
                source_remuneration_url=member.source_remuneration_url,
                payroll_type=member.payroll_type,
                exercise_date=member.exercise_date,
                source=member.source,
                source_url=member.source_url,
                collected_at=member.collected_at.isoformat(),
                source_record_id=str(member.source_record_id),
            )
            for member in members
        ],
        total=total,
        limit=limit,
        offset=offset,
        year=selected_year,
        month=selected_month,
        source=staff_summary.source if staff_summary else None,
        source_url=staff_summary.source_query_url if staff_summary else None,
        collected_at=staff_summary.collected_at.isoformat() if staff_summary else None,
        source_record_id=str(staff_summary.source_record_id) if staff_summary else None,
    )


def authorship_identity(person: Parliamentarian):
    if person.source == "senado":
        return (
            (Authorship.parliamentarian_id == person.id)
            & Authorship.author_key.startswith(f"senador:{person.external_id}:", autoescape=True)
            & (Authorship.source_record_id == Proposition.source_record_id)
        )
    return or_(
        Authorship.parliamentarian_id == person.id,
        Authorship.author_name.ilike(person.name),
    )


def published_votes(person: Parliamentarian):
    filters = [Vote.parliamentarian_id == person.id]
    if person.source == "senado":
        # "registrado" era preenchido pelo coletor antigo quando a fonte omitia a posição.
        filters.extend((Vote.source == "senado", Vote.position != "registrado"))
    return filters


@router.get("/{person_id}/authored-propositions", response_model=AuthoredPropositionPage)
def list_authored_propositions(
    person_id: UUID,
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=100000),
    db: Session = Depends(database_session),
):
    person = db.get(Parliamentarian, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Parlamentar não encontrado")
    authorship_exists = (
        select(Authorship.id)
        .where(
            Authorship.proposition_id == Proposition.id,
            Authorship.source == person.source,
            authorship_identity(person),
        )
        .exists()
    )
    query = select(Proposition).where(authorship_exists)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    propositions = db.scalars(
        query.order_by(Proposition.presented_at.desc().nullslast(), Proposition.id)
        .offset(offset)
        .limit(limit)
    ).all()
    return AuthoredPropositionPage(
        items=[
            AuthoredPropositionResponse(
                id=proposition.id,
                label=proposition_label(proposition),
                summary=proposition.summary,
                presented_at=(
                    proposition.presented_at.isoformat() if proposition.presented_at else None
                ),
                source_url=proposition.source_url,
            )
            for proposition in propositions
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{person_id}/votes", response_model=VoteRecordPage)
def list_parliamentarian_votes(
    person_id: UUID,
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=100000),
    db: Session = Depends(database_session),
):
    person = db.get(Parliamentarian, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Parlamentar não encontrado")
    query = (
        select(Vote, Voting)
        .join(Voting, Voting.id == Vote.voting_id)
        .where(*published_votes(person))
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(
            Voting.occurred_on.desc().nullslast(),
            Voting.registered_at.desc().nullslast(),
            Voting.id,
        )
        .offset(offset)
        .limit(limit)
    ).all()
    return VoteRecordPage(
        items=[
            VoteRecordResponse(
                voting_id=voting.id,
                occurred_on=voting.occurred_on.isoformat() if voting.occurred_on else None,
                description=voting.description,
                object_description=voting.object_description,
                position=vote.position,
                party_at_vote=vote.party_at_vote,
                state_at_vote=vote.state_at_vote,
                source_url=voting.source_url,
            )
            for vote, voting in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


def _csv_text(value: str | None) -> str:
    text = value or ""
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


@router.get("/{person_id}/amendments.csv")
def download_parliamentarian_amendments(
    person_id: UUID,
    year: int | None = Query(default=None, ge=2000, le=2100),
    db: Session = Depends(database_session),
):
    person = db.get(Parliamentarian, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Parlamentar não encontrado")
    selected_year = year or db.scalar(
        select(func.max(ParliamentaryAmendment.year)).where(
            ParliamentaryAmendment.parliamentarian_id == person_id,
            ParliamentaryAmendment.source == "portal_transparencia",
        )
    )
    if selected_year is None:
        raise HTTPException(
            status_code=404, detail="Não há emendas coletadas para este parlamentar"
        )
    rows = db.scalars(
        select(ParliamentaryAmendment)
        .where(
            ParliamentaryAmendment.parliamentarian_id == person_id,
            ParliamentaryAmendment.source == "portal_transparencia",
            ParliamentaryAmendment.year == selected_year,
        )
        .order_by(ParliamentaryAmendment.external_id)
    ).all()
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(
        [
            "Parlamentar",
            "Código da emenda",
            "Ano",
            "Tipo de emenda",
            "Destino",
            "Município",
            "UF",
            "Função",
            "Subfunção",
            "Programa",
            "Ação",
            "Plano orçamentário",
            "Valor empenhado (R$)",
            "Valor liquidado (R$)",
            "Valor pago (R$)",
            "Órgão publicador",
            "Página oficial do conjunto",
            "Coletado pelo portal em",
        ]
    )
    source_url = "https://portaldatransparencia.gov.br/emendas/consulta"
    for row in rows:
        writer.writerow(
            [
                _csv_text(person.name),
                _csv_text(row.external_id),
                row.year,
                _csv_text(row.amendment_type),
                _csv_text(row.locality),
                _csv_text(row.municipality),
                _csv_text(row.state),
                _csv_text(row.function_name),
                _csv_text(row.subfunction_name),
                _csv_text(row.program_name),
                _csv_text(row.action_name),
                _csv_text(row.plan_name),
                format_brazilian_amount(row.committed_amount),
                format_brazilian_amount(row.liquidated_amount),
                format_brazilian_amount(row.paid_amount),
                "Portal da Transparência do Governo Federal (CGU)",
                _csv_text(row.source_url or source_url),
                row.collected_at.isoformat(),
            ]
        )
    safe_name = re.sub(r"[^a-z0-9]+", "-", person.name.lower()).strip("-") or "parlamentar"
    filename = f"emendas-{safe_name}-{selected_year}.csv"
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{person_id}/amendments.pdf")
def download_parliamentarian_amendments_pdf(
    person_id: UUID,
    year: int | None = Query(default=None, ge=2000, le=2100),
    db: Session = Depends(database_session),
):
    person = db.get(Parliamentarian, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Parlamentar não encontrado")
    selected_year = year or db.scalar(
        select(func.max(ParliamentaryAmendment.year)).where(
            ParliamentaryAmendment.parliamentarian_id == person_id,
            ParliamentaryAmendment.source == "portal_transparencia",
        )
    )
    if selected_year is None:
        raise HTTPException(
            status_code=404, detail="Não há emendas coletadas para este parlamentar"
        )
    rows = db.scalars(
        select(ParliamentaryAmendment)
        .where(
            ParliamentaryAmendment.parliamentarian_id == person_id,
            ParliamentaryAmendment.source == "portal_transparencia",
            ParliamentaryAmendment.year == selected_year,
        )
        .order_by(ParliamentaryAmendment.external_id)
    ).all()
    mandate = db.scalar(
        select(Mandate)
        .where(Mandate.parliamentarian_id == person_id)
        .order_by(Mandate.legislature_external_id.desc())
    )
    pdf = build_amendments_pdf(person, mandate, selected_year, rows)
    safe_name = re.sub(r"[^a-z0-9]+", "-", person.name.lower()).strip("-") or "parlamentar"
    filename = f"relatorio-emendas-{safe_name}-{selected_year}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{person_id}/staff.pdf")
def download_parliamentarian_staff_pdf(
    person_id: UUID,
    db: Session = Depends(database_session),
):
    person = db.get(Parliamentarian, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Parlamentar não encontrado")
    staff = db.scalar(
        select(ParliamentaryStaffSummary)
        .where(ParliamentaryStaffSummary.parliamentarian_id == person_id)
        .order_by(ParliamentaryStaffSummary.year.desc(), ParliamentaryStaffSummary.month.desc())
    )
    if staff is None:
        raise HTTPException(status_code=404, detail="Não há equipe coletada para este parlamentar")
    staff_members = db.scalars(
        select(ParliamentaryStaffMember)
        .where(
            ParliamentaryStaffMember.parliamentarian_id == person_id,
            ParliamentaryStaffMember.source == staff.source,
            ParliamentaryStaffMember.year == staff.year,
            ParliamentaryStaffMember.month == staff.month,
        )
        .order_by(ParliamentaryStaffMember.name)
    ).all()
    mandate = db.scalar(
        select(Mandate)
        .where(Mandate.parliamentarian_id == person_id)
        .order_by(Mandate.legislature_external_id.desc())
    )
    pdf = build_staff_pdf(person, mandate, staff, staff_members)
    safe_name = re.sub(r"[^a-z0-9]+", "-", person.name.lower()).strip("-") or "parlamentar"
    filename = f"relatorio-equipe-{safe_name}-{staff.year}-{staff.month:02d}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{person_id}", response_model=ParliamentarianDetail)
def get_parliamentarian(person_id: UUID, db: Session = Depends(database_session)):
    person = db.get(Parliamentarian, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Parlamentar não encontrado")
    mandates = db.scalars(
        select(Mandate)
        .where(Mandate.parliamentarian_id == person.id)
        .order_by(Mandate.legislature_external_id.desc())
    ).all()
    current = mandates[0] if mandates else None
    item = summary(person, current)
    election = db.scalar(
        select(ElectionResult)
        .where(ElectionResult.parliamentarian_id == person.id)
        .order_by(ElectionResult.election_year.desc(), ElectionResult.election_round.desc())
    )
    authored_query = (
        select(Proposition, Authorship)
        .join(Authorship, Authorship.proposition_id == Proposition.id)
        .where(
            Authorship.source == person.source,
            authorship_identity(person),
        )
        .order_by(Proposition.presented_at.desc().nullslast(), Proposition.id)
    )
    authored_rows = db.execute(authored_query).all()
    authored_by_id = {proposition.id: proposition for proposition, _ in authored_rows}
    authored_propositions = list(authored_by_id.values())
    vote_rows = db.execute(
        select(Vote.position, func.count(Vote.id))
        .where(*published_votes(person))
        .group_by(Vote.position)
    ).all()
    votes_by_position = {position: count for position, count in vote_rows}
    recent_vote_rows = db.execute(
        select(Vote, Voting)
        .join(Voting, Voting.id == Vote.voting_id)
        .where(*published_votes(person))
        .order_by(
            Voting.occurred_on.desc().nullslast(),
            Voting.registered_at.desc().nullslast(),
            Voting.id,
        )
        .limit(8)
    ).all()
    financial_row = db.execute(
        select(
            func.count(ParliamentaryExpense.id),
            func.sum(ParliamentaryExpense.amount_net),
            func.sum(ParliamentaryExpense.amount_glossed),
            func.min(ParliamentaryExpense.year),
            func.max(ParliamentaryExpense.year),
        ).where(ParliamentaryExpense.parliamentarian_id == person.id)
    ).one()
    expense_count, net_total, glossed_total, financial_year_from, financial_year = financial_row
    financial_source_url = db.scalar(
        select(ParliamentaryExpense.source_url)
        .where(ParliamentaryExpense.parliamentarian_id == person.id)
        .order_by(ParliamentaryExpense.year.desc())
        .limit(1)
    )
    financial_collected_at = db.scalar(
        select(func.max(ParliamentaryExpense.collected_at)).where(
            ParliamentaryExpense.parliamentarian_id == person.id
        )
    )
    remuneration = db.scalar(
        select(ParliamentaryRemuneration)
        .where(ParliamentaryRemuneration.parliamentarian_id == person.id)
        .order_by(ParliamentaryRemuneration.year.desc(), ParliamentaryRemuneration.month.desc())
        .limit(1)
    )
    staff = db.scalar(
        select(ParliamentaryStaffSummary)
        .where(ParliamentaryStaffSummary.parliamentarian_id == person.id)
        .order_by(ParliamentaryStaffSummary.year.desc(), ParliamentaryStaffSummary.month.desc())
        .limit(1)
    )
    amendments = db.scalar(
        select(ParliamentaryAmendmentSummary)
        .where(ParliamentaryAmendmentSummary.parliamentarian_id == person.id)
        .order_by(ParliamentaryAmendmentSummary.year.desc())
        .limit(1)
    )
    subsidy = subsidy_reference(person.source)
    return ParliamentarianDetail(
        **item.model_dump(),
        birth_date=person.birth_date.isoformat() if person.birth_date else None,
        profile_source_url=(
            f"https://dadosabertos.camara.leg.br/api/v2/deputados/{person.external_id}"
            if person.profile_source_record_id
            else None
        ),
        # A ausência de resultado não é convertida em zero.
        election_votes=election.votes if election else None,
        election_year=election.election_year if election else None,
        election_status=election.election_status if election else None,
        election_source_url=election.source_url if election else None,
        mandate_started_on=(
            current.started_on.isoformat()
            if person.source != "senado" and current and current.started_on
            else None
        ),
        mandate_ended_on=(
            current.ended_on.isoformat()
            if person.source != "senado" and current and current.ended_on
            else None
        ),
        mandates=[
            MandateResponse(
                legislature=m.legislature_external_id,
                state=m.state,
                party=m.party,
                started_on=(
                    m.started_on.isoformat() if m.source != "senado" and m.started_on else None
                ),
                ended_on=(m.ended_on.isoformat() if m.source != "senado" and m.ended_on else None),
                source_url=m.source_url,
                source=m.source,
                collected_at=m.collected_at.isoformat(),
            )
            for m in mandates
        ],
        authored_propositions=[
            AuthoredPropositionResponse(
                id=proposition.id,
                label=proposition_label(proposition),
                summary=proposition.summary,
                presented_at=(
                    proposition.presented_at.isoformat() if proposition.presented_at else None
                ),
                source_url=proposition.source_url,
            )
            for proposition in authored_propositions[:8]
        ],
        authored_propositions_total=len(authored_propositions),
        vote_records=[
            VoteRecordResponse(
                voting_id=voting.id,
                occurred_on=voting.occurred_on.isoformat() if voting.occurred_on else None,
                description=voting.description,
                object_description=voting.object_description,
                position=vote.position,
                party_at_vote=vote.party_at_vote,
                state_at_vote=vote.state_at_vote,
                source_url=voting.source_url,
            )
            for vote, voting in recent_vote_rows
        ],
        votes_total=sum(votes_by_position.values()),
        votes_by_position=votes_by_position,
        financial_summary=FinancialSummaryResponse(
            available=bool(expense_count),
            year_from=financial_year_from,
            year=financial_year,
            expense_count=expense_count,
            net_total=net_total,
            glossed_total=glossed_total,
            source_url=financial_source_url,
            expense_source="camara" if expense_count else None,
            expense_collected_at=(
                financial_collected_at.isoformat() if financial_collected_at else None
            ),
            subsidy_reference=subsidy[0] if subsidy else None,
            subsidy_source_url=subsidy[1] if subsidy else None,
            subsidy_note=subsidy[2] if subsidy else None,
            remuneration_year=remuneration.year if remuneration else None,
            remuneration_month=remuneration.month if remuneration else None,
            remuneration_fixed=remuneration.fixed_amount if remuneration else None,
            remuneration_net=remuneration.net_amount if remuneration else None,
            remuneration_source_url=remuneration.source_document_url if remuneration else None,
            remuneration_source=remuneration.source if remuneration else None,
            remuneration_collected_at=(
                remuneration.collected_at.isoformat() if remuneration else None
            ),
            staff_count=staff.staff_count if staff else None,
            staff_year=staff.year if staff else None,
            staff_month=staff.month if staff else None,
            staff_source_url=staff.source_query_url if staff else None,
            staff_source=staff.source if staff else None,
            staff_collected_at=staff.collected_at.isoformat() if staff else None,
            amendment_year=amendments.year if amendments else None,
            amendment_count=amendments.amendment_count if amendments else None,
            amendment_committed=amendments.committed_amount if amendments else None,
            amendment_liquidated=amendments.liquidated_amount if amendments else None,
            amendment_paid=amendments.paid_amount if amendments else None,
            amendment_source_url=amendments.source_query_url if amendments else None,
            amendment_source=amendments.source if amendments else None,
            amendment_collected_at=amendments.collected_at.isoformat() if amendments else None,
        ),
    )
