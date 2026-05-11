"""create intake_answers table with foreign keys and indexes

Revision ID: 20260511_04
Revises: 20260511_03
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20260511_04"
down_revision = "20260511_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intake_answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("intake_request_id", sa.Integer(), nullable=False),
        sa.Column("question_matrix_id", sa.Integer(), nullable=False),
        sa.Column("answer_value", sa.Text(), nullable=True),
        sa.Column("answered_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["intake_request_id"], ["intake_request.id"], name="fk_intake_answers_intake_request_id"),
        sa.ForeignKeyConstraint(["question_matrix_id"], ["question_matrix.id"], name="fk_intake_answers_question_matrix_id"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_intake_answers_question_matrix_id",
        "intake_answers",
        ["question_matrix_id"],
        unique=False,
    )
    op.create_index(
        "ix_intake_answers_intake_question",
        "intake_answers",
        ["intake_request_id", "question_matrix_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_intake_answers_intake_question", table_name="intake_answers")
    op.drop_index("ix_intake_answers_question_matrix_id", table_name="intake_answers")
    op.drop_table("intake_answers")
