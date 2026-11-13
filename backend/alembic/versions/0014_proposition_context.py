"""Add official proposition context and mark documented nominal votings.

Revision ID: 0014
Revises: 0013
"""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("propositions", sa.Column("detailed_summary", sa.Text(), nullable=True))
    op.add_column("propositions", sa.Column("full_text_url", sa.String(1000), nullable=True))
    op.add_column("propositions", sa.Column("keywords", sa.JSON(), nullable=True))
    op.add_column("propositions", sa.Column("status_description", sa.Text(), nullable=True))
    op.add_column("propositions", sa.Column("status_agency", sa.String(100), nullable=True))
    op.add_column("propositions", sa.Column("status_appreciation", sa.String(250), nullable=True))
    op.add_column("propositions", sa.Column("status_regime", sa.String(250), nullable=True))
    op.add_column("propositions", sa.Column("status_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "propositions",
        sa.Column("official_detail_collected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        """
        UPDATE votings
        SET mode = 'nominal'
        WHERE mode IS NULL
          AND EXISTS (SELECT 1 FROM votes WHERE votes.voting_id = votings.id)
        """
    )


def downgrade() -> None:
    op.drop_column("propositions", "official_detail_collected_at")
    op.drop_column("propositions", "status_at")
    op.drop_column("propositions", "status_regime")
    op.drop_column("propositions", "status_appreciation")
    op.drop_column("propositions", "status_agency")
    op.drop_column("propositions", "status_description")
    op.drop_column("propositions", "keywords")
    op.drop_column("propositions", "full_text_url")
    op.drop_column("propositions", "detailed_summary")
