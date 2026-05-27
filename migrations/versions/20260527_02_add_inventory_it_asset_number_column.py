"""add it_asset_number column to inventory

Revision ID: 20260527_02
Revises: 20260527_01
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '20260527_02'
down_revision = '20260527_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    existing_cols = {col['name'] for col in inspector.get_columns('inventory')}
    if 'it_asset_number' not in existing_cols:
        op.add_column('inventory', sa.Column('it_asset_number', sa.String(length=100), nullable=True))

    existing_indexes = {idx['name'] for idx in inspector.get_indexes('inventory')}
    if 'ix_inventory_it_asset_number' not in existing_indexes:
        op.create_index('ix_inventory_it_asset_number', 'inventory', ['it_asset_number'], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    existing_indexes = {idx['name'] for idx in inspector.get_indexes('inventory')}
    if 'ix_inventory_it_asset_number' in existing_indexes:
        op.drop_index('ix_inventory_it_asset_number', table_name='inventory')

    existing_cols = {col['name'] for col in inspector.get_columns('inventory')}
    if 'it_asset_number' in existing_cols:
        op.drop_column('inventory', 'it_asset_number')
