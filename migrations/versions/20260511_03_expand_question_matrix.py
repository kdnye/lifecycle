"""Expand question_matrix with builder columns.

Revision ID: 20260511_03
Revises: 20260510_02
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa

revision = '20260511_03'
down_revision = '20260510_02'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'question_matrix',
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'question_matrix',
        sa.Column('intake_step', sa.Integer(), nullable=False, server_default='2'),
    )
    op.add_column(
        'question_matrix',
        sa.Column('field_type', sa.String(32), nullable=False, server_default='boolean'),
    )
    op.add_column(
        'question_matrix',
        sa.Column('field_options', sa.Text(), nullable=True),
    )
    op.add_column(
        'question_matrix',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    )
    op.create_index(
        'ix_question_matrix_intake_step', 'question_matrix', ['intake_step']
    )
    op.create_index(
        'ix_question_matrix_role_profile', 'question_matrix', ['role_profile']
    )


def downgrade() -> None:
    op.drop_index('ix_question_matrix_role_profile', table_name='question_matrix')
    op.drop_index('ix_question_matrix_intake_step', table_name='question_matrix')
    op.drop_column('question_matrix', 'is_active')
    op.drop_column('question_matrix', 'field_options')
    op.drop_column('question_matrix', 'field_type')
    op.drop_column('question_matrix', 'intake_step')
    op.drop_column('question_matrix', 'sort_order')
