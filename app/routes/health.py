from flask import Blueprint, current_app, jsonify
from sqlalchemy import inspect

from app.models import (
    ACTION_MATRIX_TABLE,
    ASSET_CATEGORIES_TABLE,
    COMMUNICATION_OPTIONS_TABLE,
    DISTRIBUTION_LISTS_TABLE,
    FILE_SHARE_PERMISSIONS_TABLE,
    INTAKE_REQUEST_TABLE,
    INTAKE_ANSWERS_TABLE,
    INVENTORY_TABLE,
    QUESTION_MATRIX_TABLE,
    ROLE_MATRIX_TABLE,
    ROLE_DISTRIBUTION_LISTS_TABLE,
    ROLE_FILE_SHARE_PERMISSIONS_TABLE,
    USERS_TABLE,
    db,
)

health_bp = Blueprint("health", __name__)


@health_bp.get("/healthz")
def healthz():
    startup_issues: list[str] = current_app.config.get("STARTUP_ISSUES", [])
    if startup_issues:
        return (
            jsonify(
                {
                    "status": "unready",
                    "guidance": "Fix production configuration issues before serving traffic.",
                    "issues": startup_issues,
                }
            ),
            503,
        )

    return jsonify({"status": "ok"}), 200


@health_bp.get("/readyz")
def readyz():
    startup_issues: list[str] = current_app.config.get("STARTUP_ISSUES", [])
    if startup_issues:
        return (
            jsonify(
                {
                    "status": "unready",
                    "guidance": "Fix production configuration issues before serving traffic.",
                    "issues": startup_issues,
                }
            ),
            503,
        )

    required_tables = [
        ROLE_MATRIX_TABLE,
        QUESTION_MATRIX_TABLE,
        ACTION_MATRIX_TABLE,
        INTAKE_REQUEST_TABLE,
        USERS_TABLE,
        COMMUNICATION_OPTIONS_TABLE,
        ASSET_CATEGORIES_TABLE,
        INVENTORY_TABLE,
        INTAKE_ANSWERS_TABLE,
        DISTRIBUTION_LISTS_TABLE,
        FILE_SHARE_PERMISSIONS_TABLE,
        ROLE_DISTRIBUTION_LISTS_TABLE,
        ROLE_FILE_SHARE_PERMISSIONS_TABLE,
    ]
    required_columns = {
        ROLE_MATRIX_TABLE: ["id", "role_profile", "m365_plan", "hardware_default", "vpn_policy"],
        QUESTION_MATRIX_TABLE: ["id", "role_profile", "question_key", "prompt", "is_required"],
        ACTION_MATRIX_TABLE: ["id", "intake_condition", "action_name", "target_system"],
        INTAKE_REQUEST_TABLE: ["id", "first_name", "last_name", "role_profile", "event_type"],
        USERS_TABLE: ["id", "email", "password_hash", "can_manage_lifecycle"],
        COMMUNICATION_OPTIONS_TABLE: ["id", "it_support_email", "it_sales_email", "telecon_sales_email"],
        ASSET_CATEGORIES_TABLE: ["id", "name", "is_active"],
        INVENTORY_TABLE: ["id", "status", "created_at", "updated_at", "location", "it_asset_number"],
        INTAKE_ANSWERS_TABLE: ["id", "intake_request_id", "question_matrix_id"],
        DISTRIBUTION_LISTS_TABLE: ["id", "name", "email", "is_active"],
        FILE_SHARE_PERMISSIONS_TABLE: ["id", "name", "resource_path", "is_active"],
        ROLE_DISTRIBUTION_LISTS_TABLE: ["role_matrix_id", "distribution_list_id"],
        ROLE_FILE_SHARE_PERMISSIONS_TABLE: ["role_matrix_id", "file_share_permission_id"],
    }

    missing_tables: list[str] = []
    missing_columns: dict[str, list[str]] = {}
    try:
        inspector = inspect(db.engine)
        existing = set(inspector.get_table_names())
        missing_tables = [table for table in required_tables if table not in existing]

        for table_name, columns in required_columns.items():
            if table_name in missing_tables:
                continue
            present = {col["name"] for col in inspector.get_columns(table_name)}
            missing_for_table = [col for col in columns if col not in present]
            if missing_for_table:
                missing_columns[table_name] = missing_for_table
    except Exception as exc:  # readiness must be actionable, never opaque
        return (
            jsonify(
                {
                    "status": "unready",
                    "guidance": "Database unavailable. Verify DATABASE_URL and migrations.",
                    "error": str(exc),
                }
            ),
            503,
        )

    if missing_tables or missing_columns:
        return (
            jsonify(
                {
                    "status": "unready",
                    "guidance": "Run `flask db upgrade` or `alembic upgrade head`.",
                    "missing_tables": missing_tables,
                    "missing_columns": missing_columns,
                }
            ),
            503,
        )

    return jsonify({"status": "ready"}), 200
