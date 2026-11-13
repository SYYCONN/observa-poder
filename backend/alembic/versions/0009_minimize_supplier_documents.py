"""Remove documentos de fornecedores sem uso na consulta pública.

Revision ID: 0009
Revises: 0008
"""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # O campo da fonte mistura CPF e CNPJ. Nenhum deles é necessário à UI/API.
    op.drop_column("parliamentary_expenses", "supplier_document")


def downgrade() -> None:
    # Restaura somente a estrutura; documentos removidos não são recuperados.
    op.add_column(
        "parliamentary_expenses", sa.Column("supplier_document", sa.String(40), nullable=True)
    )
