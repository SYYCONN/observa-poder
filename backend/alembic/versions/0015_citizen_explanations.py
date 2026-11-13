"""Add reviewed citizen explanations for propositions.

Revision ID: 0015
Revises: 0014
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proposition_citizen_explanations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposition_id", sa.Uuid(), nullable=False),
        sa.Column("plain_summary", sa.Text(), nullable=False),
        sa.Column("what_changes", sa.Text(), nullable=True),
        sa.Column("affected_groups", sa.JSON(), nullable=True),
        sa.Column("practical_example", sa.Text(), nullable=True),
        sa.Column("impacts", sa.Text(), nullable=True),
        sa.Column("benefits", sa.Text(), nullable=True),
        sa.Column("cost_estimate", sa.Text(), nullable=True),
        sa.Column("analysis", sa.Text(), nullable=True),
        sa.Column("source_basis", sa.JSON(), nullable=True),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("review_status", sa.String(20), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "method IN ('editorial', 'assisted')",
            name="citizen_explanation_method",
        ),
        sa.CheckConstraint(
            "review_status IN ('draft', 'reviewed', 'published')",
            name="citizen_explanation_review_status",
        ),
        sa.ForeignKeyConstraint(["proposition_id"], ["propositions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposition_id"),
    )
    op.create_index(
        "ix_proposition_citizen_explanations_proposition_id",
        "proposition_citizen_explanations",
        ["proposition_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_proposition_citizen_explanations_proposition_id",
        table_name="proposition_citizen_explanations",
    )
    op.drop_table("proposition_citizen_explanations")
