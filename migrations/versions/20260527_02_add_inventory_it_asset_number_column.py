"""add it_asset_number column to inventory

Revision ID: 20260527_02
Revises: 20260527_01
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa

revision = '20260527_02'
down_revision = '20260527_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('inventory', sa.Column('it_asset_number', sa.String(length=100), nullable=True))
    op.create_index('ix_inventory_it_asset_number', 'inventory', ['it_asset_number'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_inventory_it_asset_number', table_name='inventory')
    op.drop_column('inventory', 'it_asset_number')
