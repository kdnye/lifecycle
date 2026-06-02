"""seed BLE Beacon inventory category

Revision ID: 20260602_01
Revises: 20260527_02
Create Date: 2026-06-02
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = "20260602_01"
down_revision = "20260527_02"
branch_labels = None
depends_on = None


asset_categories = sa.table(
    "asset_categories",
    sa.column("id", sa.Integer),
    sa.column("name", sa.String),
    sa.column("parent_category_id", sa.Integer),
    sa.column("is_active", sa.Boolean),
    sa.column("created_at", sa.DateTime),
)


def upgrade() -> None:
    bind = op.get_bind()
    existing = bind.execute(
        sa.select(asset_categories.c.id).where(
            asset_categories.c.name == "BLE Beacon",
            asset_categories.c.parent_category_id.is_(None),
        )
    ).first()
    if existing is None:
        op.bulk_insert(
            asset_categories,
            [
                {
                    "name": "BLE Beacon",
                    "parent_category_id": None,
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                }
            ],
        )


def downgrade() -> None:
    # Intentionally keep this reference category on downgrade; by the time it
    # exists it may be assigned to inventory rows that outlive this revision.
    pass
