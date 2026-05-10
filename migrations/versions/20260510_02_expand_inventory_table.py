"""expand inventory table: add asset_status enum, new columns, drop device_type

Revision ID: 20260510_02
Revises: 20260510_01
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa

revision = '20260510_02'
down_revision = '20260510_01'
branch_labels = None
depends_on = None

_ASSET_STATUS_VALUES = ('Available', 'Assigned', 'In_Repair', 'Retired', 'Lost')


def upgrade() -> None:
    # Create the PostgreSQL enum type first (checkfirst=True is idempotent)
    asset_status = sa.Enum(*_ASSET_STATUS_VALUES, name='asset_status')
    asset_status.create(op.get_bind(), checkfirst=True)

    # Add all new columns (nullable or with server_default so existing rows are safe)
    op.add_column('inventory',
        sa.Column('asset_tag', sa.String(100), nullable=True))
    op.add_column('inventory',
        sa.Column('ble_tag_id', sa.String(100), nullable=True))
    op.add_column('inventory',
        sa.Column('category_id', sa.Integer(), nullable=True))
    op.add_column('inventory',
        sa.Column('make', sa.String(100), nullable=True))
    op.add_column('inventory',
        sa.Column('model_name', sa.String(100), nullable=True))
    op.add_column('inventory',
        sa.Column(
            'status',
            sa.Enum(*_ASSET_STATUS_VALUES, name='asset_status'),
            nullable=False,
            server_default='Available',
        ))
    op.add_column('inventory',
        sa.Column('assigned_to_user_id', sa.Integer(), nullable=True))
    op.add_column('inventory',
        sa.Column('photo_url', sa.String(1024), nullable=True))
    op.add_column('inventory',
        sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('inventory',
        sa.Column('purchase_date', sa.Date(), nullable=True))
    op.add_column('inventory',
        sa.Column('purchase_price', sa.Numeric(10, 2), nullable=True))
    op.add_column('inventory',
        sa.Column('warranty_expiry', sa.Date(), nullable=True))
    op.add_column('inventory',
        sa.Column(
            'updated_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('now()'),
        ))

    # Make serial_number nullable (was NOT NULL in the stub)
    op.alter_column('inventory', 'serial_number', nullable=True)

    # Unique indexes for tag fields
    op.create_index('ix_inventory_asset_tag',
                    'inventory', ['asset_tag'], unique=True)
    op.create_index('ix_inventory_ble_tag_id',
                    'inventory', ['ble_tag_id'], unique=True)
    op.create_index('ix_inventory_category_id',
                    'inventory', ['category_id'])
    op.create_index('ix_inventory_assigned_to_user_id',
                    'inventory', ['assigned_to_user_id'])

    # Foreign keys
    op.create_foreign_key(
        'fk_inventory_category_id',
        'inventory', 'asset_categories',
        ['category_id'], ['id'],
    )
    op.create_foreign_key(
        'fk_inventory_assigned_to_user_id',
        'inventory', 'users',
        ['assigned_to_user_id'], ['id'],
    )

    # Drop the old device_type column (replaced by category_id + make/model_name)
    op.drop_column('inventory', 'device_type')


def downgrade() -> None:
    op.add_column('inventory',
        sa.Column('device_type', sa.String(64), nullable=False,
                  server_default='Laptop'))

    op.drop_constraint('fk_inventory_assigned_to_user_id',
                       'inventory', type_='foreignkey')
    op.drop_constraint('fk_inventory_category_id',
                       'inventory', type_='foreignkey')

    op.drop_index('ix_inventory_assigned_to_user_id', table_name='inventory')
    op.drop_index('ix_inventory_category_id', table_name='inventory')
    op.drop_index('ix_inventory_ble_tag_id', table_name='inventory')
    op.drop_index('ix_inventory_asset_tag', table_name='inventory')

    op.alter_column('inventory', 'serial_number', nullable=False)

    op.drop_column('inventory', 'updated_at')
    op.drop_column('inventory', 'warranty_expiry')
    op.drop_column('inventory', 'purchase_price')
    op.drop_column('inventory', 'purchase_date')
    op.drop_column('inventory', 'notes')
    op.drop_column('inventory', 'photo_url')
    op.drop_column('inventory', 'assigned_to_user_id')
    op.drop_column('inventory', 'status')
    op.drop_column('inventory', 'model_name')
    op.drop_column('inventory', 'make')
    op.drop_column('inventory', 'category_id')
    op.drop_column('inventory', 'ble_tag_id')
    op.drop_column('inventory', 'asset_tag')

    sa.Enum(name='asset_status').drop(op.get_bind(), checkfirst=True)

    op.drop_table('asset_categories')
