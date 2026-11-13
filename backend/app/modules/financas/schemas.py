from decimal import Decimal

from pydantic import BaseModel


class FinancialSummaryResponse(BaseModel):
    available: bool
    year_from: int | None
    year: int | None
    expense_count: int
    net_total: Decimal | None
    glossed_total: Decimal | None
    source_url: str | None
    expense_source: str | None = None
    expense_collected_at: str | None = None
    subsidy_reference: Decimal | None = None
    subsidy_source_url: str | None = None
    subsidy_note: str | None = None
    remuneration_year: int | None = None
    remuneration_month: int | None = None
    remuneration_fixed: Decimal | None = None
    remuneration_net: Decimal | None = None
    remuneration_source_url: str | None = None
    remuneration_source: str | None = None
    remuneration_collected_at: str | None = None
    staff_count: int | None = None
    staff_year: int | None = None
    staff_month: int | None = None
    staff_source_url: str | None = None
    staff_source: str | None = None
    staff_collected_at: str | None = None
    amendment_year: int | None = None
    amendment_count: int | None = None
    amendment_committed: Decimal | None = None
    amendment_liquidated: Decimal | None = None
    amendment_paid: Decimal | None = None
    amendment_source_url: str | None = None
    amendment_source: str | None = None
    amendment_collected_at: str | None = None


class ParliamentaryExpenseResponse(BaseModel):
    id: str
    external_id: str
    year: int
    occurred_on: str | None
    month: int | None
    category: str
    category_detail: str | None
    supplier_name: str | None
    document_number: str | None
    document_type: str | None
    amount_document: Decimal | None
    amount_glossed: Decimal | None
    amount_net: Decimal | None
    reimbursement: str | None
    source_document_url: str | None
    source: str
    source_url: str
    collected_at: str
    source_record_id: str


class ParliamentaryExpensePage(BaseModel):
    items: list[ParliamentaryExpenseResponse]
    total: int
    limit: int
    offset: int
    year: int | None


class ParliamentaryStaffMemberResponse(BaseModel):
    id: str
    external_id: str
    name: str
    category: str | None
    area_of_work: str | None
    job_title: str | None
    level: str | None
    gross_amount: Decimal | None
    net_amount: Decimal | None
    allowances_amount: Decimal | None
    source_query_url: str
    source_remuneration_url: str | None
    payroll_type: str | None
    exercise_date: str | None
    source: str
    source_url: str
    collected_at: str
    source_record_id: str


class ParliamentaryStaffPage(BaseModel):
    items: list[ParliamentaryStaffMemberResponse]
    total: int
    limit: int
    offset: int
    year: int | None
    month: int | None
    source: str | None = None
    source_url: str | None = None
    collected_at: str | None = None
    source_record_id: str | None = None
