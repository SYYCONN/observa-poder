"""parliamentary amendment summary

Revision ID: 0006
Revises: 0005
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parliamentary_amendment_summaries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parliamentarian_id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("amendment_count", sa.Integer(), nullable=False),
        sa.Column("committed_amount", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("liquidated_amount", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("paid_amount", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("source_query_url", sa.String(length=1000), nullable=False),
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
            name="uq_parliamentary_amendment_summary_person_source_year",
        ),
    )
    op.create_index(
        "ix_parliamentary_amendment_summaries_parliamentarian_id",
        "parliamentary_amendment_summaries",
        ["parliamentarian_id"],
    )
    op.create_index(
        "ix_parliamentary_amendment_summaries_year",
        "parliamentary_amendment_summaries",
        ["year"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_parliamentary_amendment_summaries_year",
        table_name="parliamentary_amendment_summaries",
    )
    op.drop_index(
        "ix_parliamentary_amendment_summaries_parliamentarian_id",
        table_name="parliamentary_amendment_summaries",
    )
    op.drop_table("parliamentary_amendment_summaries")
