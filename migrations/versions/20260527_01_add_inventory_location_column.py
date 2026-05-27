"""add location column to inventory

Revision ID: 20260527_01
Revises: 20260521_01
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '20260527_01'
down_revision = '20260521_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_cols = {col['name'] for col in inspector.get_columns('inventory')}
    if 'location' not in existing_cols:
        op.add_column('inventory', sa.Column('location', sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_cols = {col['name'] for col in inspector.get_columns('inventory')}
    if 'location' in existing_cols:
        op.drop_column('inventory', 'location')
