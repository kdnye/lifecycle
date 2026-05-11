"""create distribution and file-share permission tables

Revision ID: 20260511_05
Revises: 20260511_04
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20260511_05"
down_revision = "20260511_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "distribution_lists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_distribution_lists_name"),
        sa.UniqueConstraint("email", name="uq_distribution_lists_email"),
    )

    op.create_table(
        "file_share_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("resource_path", sa.String(length=512), nullable=False),
        sa.Column("access_level", sa.String(length=64), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_file_share_permissions_name"),
        sa.UniqueConstraint("resource_path", name="uq_file_share_permissions_resource_path"),
    )

    op.create_table(
        "role_distribution_lists",
        sa.Column("role_matrix_id", sa.Integer(), nullable=False),
        sa.Column("distribution_list_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["role_matrix_id"], ["role_matrix.id"], name="fk_role_distribution_lists_role_matrix_id"),
        sa.ForeignKeyConstraint(["distribution_list_id"], ["distribution_lists.id"], name="fk_role_distribution_lists_distribution_list_id"),
        sa.PrimaryKeyConstraint("role_matrix_id", "distribution_list_id"),
    )

    op.create_table(
        "role_file_share_permissions",
        sa.Column("role_matrix_id", sa.Integer(), nullable=False),
        sa.Column("file_share_permission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["role_matrix_id"], ["role_matrix.id"], name="fk_role_file_share_permissions_role_matrix_id"),
        sa.ForeignKeyConstraint(["file_share_permission_id"], ["file_share_permissions.id"], name="fk_role_file_share_permissions_file_share_permission_id"),
        sa.PrimaryKeyConstraint("role_matrix_id", "file_share_permission_id"),
    )

    op.create_index("ix_role_distribution_lists_distribution_list_id", "role_distribution_lists", ["distribution_list_id"], unique=False)
    op.create_index("ix_role_file_share_permissions_file_share_permission_id", "role_file_share_permissions", ["file_share_permission_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_role_file_share_permissions_file_share_permission_id", table_name="role_file_share_permissions")
    op.drop_index("ix_role_distribution_lists_distribution_list_id", table_name="role_distribution_lists")

    op.drop_table("role_file_share_permissions")
    op.drop_table("role_distribution_lists")
    op.drop_table("file_share_permissions")
    op.drop_table("distribution_lists")
