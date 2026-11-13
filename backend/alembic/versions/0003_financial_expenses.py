"""financial expenses

Revision ID: 0003
Revises: 0002
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parliamentary_expenses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("parliamentarian_id", sa.Uuid(), nullable=True),
        sa.Column("occurred_on", sa.Date(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=True),
        sa.Column("category", sa.String(length=250), nullable=False),
        sa.Column("category_detail", sa.Text(), nullable=True),
        sa.Column("supplier_name", sa.String(length=500), nullable=True),
        sa.Column("supplier_document", sa.String(length=40), nullable=True),
        sa.Column("document_number", sa.String(length=100), nullable=True),
        sa.Column("document_type", sa.String(length=50), nullable=True),
        sa.Column("amount_document", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("amount_glossed", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("amount_net", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("reimbursement", sa.String(length=100), nullable=True),
        sa.Column("source_document_url", sa.String(length=1000), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_record_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["parliamentarian_id"], ["parliamentarians.id"]),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_records.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id"),
    )
    op.create_index(
        "ix_parliamentary_expenses_parliamentarian_id",
        "parliamentary_expenses",
        ["parliamentarian_id"],
    )
    op.create_index("ix_parliamentary_expenses_occurred_on", "parliamentary_expenses", ["occurred_on"])
    op.create_index("ix_parliamentary_expenses_year", "parliamentary_expenses", ["year"])


def downgrade() -> None:
    op.drop_index("ix_parliamentary_expenses_year", table_name="parliamentary_expenses")
    op.drop_index("ix_parliamentary_expenses_occurred_on", table_name="parliamentary_expenses")
    op.drop_index(
        "ix_parliamentary_expenses_parliamentarian_id", table_name="parliamentary_expenses"
    )
    op.drop_table("parliamentary_expenses")
