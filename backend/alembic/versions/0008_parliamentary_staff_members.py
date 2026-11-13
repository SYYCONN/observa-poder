"""parliamentary staff member details

Revision ID: 0008
Revises: 0007
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parliamentary_staff_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=120), nullable=False),
        sa.Column("parliamentarian_id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("category", sa.String(length=150), nullable=True),
        sa.Column("area_of_work", sa.String(length=250), nullable=True),
        sa.Column("job_title", sa.String(length=250), nullable=True),
        sa.Column("level", sa.String(length=50), nullable=True),
        sa.Column("gross_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("net_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("allowances_amount", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("source_query_url", sa.String(length=1000), nullable=False),
        sa.Column("source_remuneration_url", sa.String(length=1000), nullable=True),
        sa.Column("payroll_type", sa.String(length=100), nullable=True),
        sa.Column("exercise_date", sa.String(length=20), nullable=True),
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
            "external_id",
            "year",
            "month",
            name="uq_parliamentary_staff_member_person_source_period",
        ),
    )
    op.create_index(
        "ix_parliamentary_staff_members_external_id",
        "parliamentary_staff_members",
        ["external_id"],
    )
    op.create_index(
        "ix_parliamentary_staff_members_parliamentarian_id",
        "parliamentary_staff_members",
        ["parliamentarian_id"],
    )
    op.create_index(
        "ix_parliamentary_staff_members_year",
        "parliamentary_staff_members",
        ["year"],
    )


def downgrade() -> None:
    op.drop_index("ix_parliamentary_staff_members_year", table_name="parliamentary_staff_members")
    op.drop_index(
        "ix_parliamentary_staff_members_parliamentarian_id",
        table_name="parliamentary_staff_members",
    )
    op.drop_index(
        "ix_parliamentary_staff_members_external_id",
        table_name="parliamentary_staff_members",
    )
    op.drop_table("parliamentary_staff_members")
