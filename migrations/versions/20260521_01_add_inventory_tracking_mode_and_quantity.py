"""add inventory tracking mode and quantity

Revision ID: 20260521_01
Revises: 20260510_02
Create Date: 2026-05-21
"""
from alembic import op
import sqlalchemy as sa

revision = '20260521_01'
down_revision = '20260510_02'
branch_labels = None
depends_on = None

_TRACKING_VALUES = ('Serialized', 'Quantity')


def upgrade() -> None:
    tracking_enum = sa.Enum(*_TRACKING_VALUES, name='asset_tracking_mode')
    tracking_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'inventory',
        sa.Column(
            'tracking_mode',
            sa.Enum(*_TRACKING_VALUES, name='asset_tracking_mode'),
            nullable=False,
            server_default='Serialized',
        ),
    )
    op.add_column(
        'inventory',
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
    )


def downgrade() -> None:
    op.drop_column('inventory', 'quantity')
    op.drop_column('inventory', 'tracking_mode')
    sa.Enum(name='asset_tracking_mode').drop(op.get_bind(), checkfirst=True)
