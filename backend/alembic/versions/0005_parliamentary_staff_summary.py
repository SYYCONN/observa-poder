"""parliamentary staff summary

Revision ID: 0005
Revises: 0004
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parliamentary_staff_summaries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parliamentarian_id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("staff_count", sa.Integer(), nullable=False),
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
            "month",
            name="uq_parliamentary_staff_summary_person_source_period",
        ),
    )
    op.create_index(
        "ix_parliamentary_staff_summaries_parliamentarian_id",
        "parliamentary_staff_summaries",
        ["parliamentarian_id"],
    )
    op.create_index(
        "ix_parliamentary_staff_summaries_year",
        "parliamentary_staff_summaries",
        ["year"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_parliamentary_staff_summaries_year",
        table_name="parliamentary_staff_summaries",
    )
    op.drop_index(
        "ix_parliamentary_staff_summaries_parliamentarian_id",
        table_name="parliamentary_staff_summaries",
    )
    op.drop_table("parliamentary_staff_summaries")
