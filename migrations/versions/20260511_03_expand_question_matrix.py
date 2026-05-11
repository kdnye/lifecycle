"""expand question_matrix with dynamic question columns

Revision ID: 20260511_03
Revises: 20260510_02
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20260511_03"
down_revision = "20260510_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "question_matrix",
        sa.Column("depends_on_question_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "question_matrix",
        sa.Column("depends_on_answer_value", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "question_matrix",
        sa.Column("visibility_rule", sa.String(length=16), nullable=False, server_default="equals"),
    )
    op.add_column(
        "question_matrix",
        sa.Column("is_dynamic", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_index(
        "ix_question_matrix_depends_on_question_key",
        "question_matrix",
        ["depends_on_question_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_question_matrix_depends_on_question_key", table_name="question_matrix")
    op.drop_column("question_matrix", "is_dynamic")
    op.drop_column("question_matrix", "visibility_rule")
    op.drop_column("question_matrix", "depends_on_answer_value")
    op.drop_column("question_matrix", "depends_on_question_key")
