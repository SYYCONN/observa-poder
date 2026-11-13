"""Store official deputy profile details with provenance.

Revision ID: 0012
Revises: 0011
"""

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("parliamentarians", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column(
        "parliamentarians",
        sa.Column("profile_collected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "parliamentarians",
        sa.Column("profile_source_record_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_parliamentarians_profile_source_record",
        "parliamentarians",
        "source_records",
        ["profile_source_record_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_parliamentarians_profile_source_record", "parliamentarians", type_="foreignkey"
    )
    op.drop_column("parliamentarians", "profile_source_record_id")
    op.drop_column("parliamentarians", "profile_collected_at")
    op.drop_column("parliamentarians", "birth_date")
