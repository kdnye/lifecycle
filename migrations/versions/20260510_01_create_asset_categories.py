"""create asset_categories table

Revision ID: 20260510_01
Revises:
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa

revision = '20260510_01'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'asset_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('parent_category_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False,
                  server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(
            ['parent_category_id'], ['asset_categories.id'],
            name='fk_asset_categories_parent_category_id',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_asset_categories_parent_category_id',
        'asset_categories',
        ['parent_category_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_asset_categories_parent_category_id',
                  table_name='asset_categories')
    op.drop_table('asset_categories')
