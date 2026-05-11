"""Create intake_answers table.

Revision ID: 20260511_04
Revises: 20260511_03
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa

revision = '20260511_04'
down_revision = '20260511_03'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'intake_answers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('intake_request_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('question_key', sa.String(128), nullable=False),
        sa.Column('answer_value', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('now()'),
        ),
        sa.ForeignKeyConstraint(
            ['intake_request_id'], ['intake_request.id'], name='fk_intake_answers_request'
        ),
        sa.ForeignKeyConstraint(
            ['question_id'], ['question_matrix.id'], name='fk_intake_answers_question'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_intake_answers_intake_request_id',
        'intake_answers',
        ['intake_request_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_intake_answers_intake_request_id', table_name='intake_answers')
    op.drop_table('intake_answers')
