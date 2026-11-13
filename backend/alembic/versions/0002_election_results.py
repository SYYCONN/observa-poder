"""election_results

Revision ID: 0002
Revises: 0001
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "election_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parliamentarian_id", sa.Uuid(), nullable=False),
        sa.Column("election_year", sa.Integer(), nullable=False),
        sa.Column("election_round", sa.Integer(), nullable=False),
        sa.Column("office", sa.String(length=80), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("candidate_number", sa.String(length=20), nullable=True),
        sa.Column("candidate_name", sa.String(length=250), nullable=False),
        sa.Column("party", sa.String(length=40), nullable=True),
        sa.Column("votes", sa.Integer(), nullable=False),
        sa.Column("valid_votes", sa.Integer(), nullable=True),
        sa.Column("election_status", sa.String(length=120), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_record_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["parliamentarian_id"], ["parliamentarians.id"]),
        sa.ForeignKeyConstraint(["source_record_id"], ["source_records.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "parliamentarian_id", "source", "election_year", "office",
            name="uq_election_result_parliamentarian_source_year_office",
        ),
    )
    op.create_index(
        op.f("ix_election_results_parliamentarian_id"),
        "election_results",
        ["parliamentarian_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_election_results_election_year"),
        "election_results",
        ["election_year"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_election_results_election_year"), table_name="election_results")
    op.drop_index(op.f("ix_election_results_parliamentarian_id"), table_name="election_results")
    op.drop_table("election_results")
