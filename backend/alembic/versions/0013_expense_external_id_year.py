"""Namespace CEAP document identifiers by year.

Revision ID: 0013
Revises: 0012
"""

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE parliamentary_expenses
        SET external_id = CAST(year AS VARCHAR) || ':' || external_id
        WHERE external_id NOT LIKE CAST(year AS VARCHAR) || ':%'
        """
    )


def downgrade() -> None:
    # O ID puro é reutilizado entre anos e não pode ser restaurado mantendo a
    # restrição única global. O prefixo é compatível com versões anteriores.
    pass
