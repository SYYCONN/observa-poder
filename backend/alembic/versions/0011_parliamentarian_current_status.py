"""Track whether a parliamentarian appears in the latest official roster.

Revision ID: 0011
Revises: 0010
"""

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "parliamentarians",
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(
        "ix_parliamentarians_is_current",
        "parliamentarians",
        ["is_current"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_parliamentarians_is_current", table_name="parliamentarians")
    op.drop_column("parliamentarians", "is_current")
