"""parliamentary monthly remuneration

Revision ID: 0004
Revises: 0003
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parliamentary_remunerations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parliamentarian_id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("payroll_type", sa.String(length=80), nullable=False),
        sa.Column("fixed_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("net_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("source_document_url", sa.String(length=1000), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_record_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["parliamentarian_id"], ["parliamentarians.id"]),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_records.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "parliamentarian_id",
            "source",
            "year",
            "month",
            "payroll_type",
            name="uq_parliamentary_remuneration_person_source_period",
        ),
    )
    op.create_index(
        "ix_parliamentary_remunerations_parliamentarian_id",
        "parliamentary_remunerations",
        ["parliamentarian_id"],
    )
    op.create_index(
        "ix_parliamentary_remunerations_year",
        "parliamentary_remunerations",
        ["year"],
    )


def downgrade() -> None:
    op.drop_index("ix_parliamentary_remunerations_year", table_name="parliamentary_remunerations")
    op.drop_index(
        "ix_parliamentary_remunerations_parliamentarian_id",
        table_name="parliamentary_remunerations",
    )
    op.drop_table("parliamentary_remunerations")
