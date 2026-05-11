"""Create distribution_lists, file_share_permissions and role association tables.

Revision ID: 20260511_05
Revises: 20260511_04
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa

revision = '20260511_05'
down_revision = '20260511_04'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'distribution_lists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email_address', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'is_active', sa.Boolean(), nullable=False, server_default='true'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('now()'),
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'file_share_permissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('share_path', sa.String(512), nullable=True),
        sa.Column(
            'access_level', sa.String(32), nullable=False, server_default='Read'
        ),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'is_active', sa.Boolean(), nullable=False, server_default='true'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('now()'),
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'role_distribution_lists',
        sa.Column('role_matrix_id', sa.Integer(), nullable=False),
        sa.Column('distribution_list_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['role_matrix_id'],
            ['role_matrix.id'],
            name='fk_role_dl_role_matrix',
        ),
        sa.ForeignKeyConstraint(
            ['distribution_list_id'],
            ['distribution_lists.id'],
            name='fk_role_dl_distribution_list',
        ),
        sa.PrimaryKeyConstraint('role_matrix_id', 'distribution_list_id'),
    )
    op.create_table(
        'role_file_share_permissions',
        sa.Column('role_matrix_id', sa.Integer(), nullable=False),
        sa.Column('file_share_permission_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['role_matrix_id'],
            ['role_matrix.id'],
            name='fk_role_share_role_matrix',
        ),
        sa.ForeignKeyConstraint(
            ['file_share_permission_id'],
            ['file_share_permissions.id'],
            name='fk_role_share_file_share',
        ),
        sa.PrimaryKeyConstraint('role_matrix_id', 'file_share_permission_id'),
    )


def downgrade() -> None:
    op.drop_table('role_file_share_permissions')
    op.drop_table('role_distribution_lists')
    op.drop_table('file_share_permissions')
    op.drop_table('distribution_lists')
