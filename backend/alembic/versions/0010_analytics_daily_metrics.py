"""Daily aggregate analytics without visitor identifiers.

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analytics_daily_metrics",
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("category", sa.String(24), primary_key=True),
        sa.Column("route", sa.String(200), primary_key=True),
        sa.Column("outcome", sa.String(8), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("analytics_daily_metrics")
