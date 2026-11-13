"""Add autonomous citizen explanation audit trail.

Revision ID: 0017
Revises: 0016
"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "citizen_explanation_method",
        "proposition_citizen_explanations",
        type_="check",
    )
    op.create_check_constraint(
        "citizen_explanation_method",
        "proposition_citizen_explanations",
        "method IN ('editorial', 'assisted', 'automated')",
    )
    op.add_column(
        "proposition_citizen_explanations", sa.Column("source_hash", sa.String(64))
    )
    op.add_column(
        "proposition_citizen_explanations", sa.Column("generation_model", sa.String(200))
    )
    op.add_column(
        "proposition_citizen_explanations", sa.Column("verification_model", sa.String(200))
    )
    op.add_column(
        "proposition_citizen_explanations", sa.Column("validation_results", sa.JSON())
    )
    op.add_column(
        "proposition_citizen_explanations",
        sa.Column("generated_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_proposition_citizen_explanations_source_hash",
        "proposition_citizen_explanations",
        ["source_hash"],
    )
    op.create_table(
        "citizen_explanation_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposition_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("generation_model", sa.String(200), nullable=False),
        sa.Column("verification_model", sa.String(200), nullable=False),
        sa.Column("prompt_version", sa.String(40), nullable=False),
        sa.Column("draft", sa.JSON()),
        sa.Column("deterministic_checks", sa.JSON()),
        sa.Column("ai_verification", sa.JSON()),
        sa.Column("error_code", sa.String(80)),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('generating', 'published', 'rejected', 'failed')",
            name="citizen_explanation_run_status",
        ),
        sa.ForeignKeyConstraint(["proposition_id"], ["propositions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_citizen_explanation_runs_proposition_id",
        "citizen_explanation_runs",
        ["proposition_id"],
    )
    op.create_index(
        "ix_citizen_explanation_runs_status", "citizen_explanation_runs", ["status"]
    )
    op.create_index(
        "ix_citizen_explanation_runs_source_hash",
        "citizen_explanation_runs",
        ["source_hash"],
    )


def downgrade() -> None:
    op.drop_table("citizen_explanation_runs")
    op.drop_index(
        "ix_proposition_citizen_explanations_source_hash",
        table_name="proposition_citizen_explanations",
    )
    for column in (
        "generated_at",
        "validation_results",
        "verification_model",
        "generation_model",
        "source_hash",
    ):
        op.drop_column("proposition_citizen_explanations", column)
    op.drop_constraint(
        "citizen_explanation_method",
        "proposition_citizen_explanations",
        type_="check",
    )
    op.create_check_constraint(
        "citizen_explanation_method",
        "proposition_citizen_explanations",
        "method IN ('editorial', 'assisted')",
    )
