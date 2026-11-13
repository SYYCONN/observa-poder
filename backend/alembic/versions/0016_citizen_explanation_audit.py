"""Add editorial review audit fields.

Revision ID: 0016
Revises: 0015
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "proposition_citizen_explanations",
        sa.Column("editor_name", sa.String(120), nullable=True),
    )
    op.add_column(
        "proposition_citizen_explanations",
        sa.Column("reviewed_by", sa.String(120), nullable=True),
    )
    op.add_column(
        "proposition_citizen_explanations",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("proposition_citizen_explanations", "published_at")
    op.drop_column("proposition_citizen_explanations", "reviewed_by")
    op.drop_column("proposition_citizen_explanations", "editor_name")
