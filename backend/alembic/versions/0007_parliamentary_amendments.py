"""parliamentary amendment details

Revision ID: 0007
Revises: 0006
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parliamentary_amendments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("parliamentarian_id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("amendment_type", sa.String(length=250), nullable=True),
        sa.Column("locality", sa.String(length=500), nullable=True),
        sa.Column("municipality", sa.String(length=250), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("function_name", sa.String(length=250), nullable=True),
        sa.Column("subfunction_name", sa.String(length=250), nullable=True),
        sa.Column("program_name", sa.Text(), nullable=True),
        sa.Column("action_name", sa.Text(), nullable=True),
        sa.Column("plan_name", sa.Text(), nullable=True),
        sa.Column("committed_amount", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("liquidated_amount", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("paid_amount", sa.Numeric(precision=16, scale=2), nullable=True),
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
            name="uq_parliamentary_amendment_person_source_external",
        ),
    )
    op.create_index(
        "ix_parliamentary_amendments_external_id",
        "parliamentary_amendments",
        ["external_id"],
    )
    op.create_index(
        "ix_parliamentary_amendments_parliamentarian_id",
        "parliamentary_amendments",
        ["parliamentarian_id"],
    )
    op.create_index("ix_parliamentary_amendments_year", "parliamentary_amendments", ["year"])


def downgrade() -> None:
    op.drop_index("ix_parliamentary_amendments_year", table_name="parliamentary_amendments")
    op.drop_index(
        "ix_parliamentary_amendments_parliamentarian_id",
        table_name="parliamentary_amendments",
    )
    op.drop_index("ix_parliamentary_amendments_external_id", table_name="parliamentary_amendments")
    op.drop_table("parliamentary_amendments")
