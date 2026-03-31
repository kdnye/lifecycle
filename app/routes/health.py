from flask import Blueprint, jsonify
from sqlalchemy import inspect

from app.models import (
    ACTION_MATRIX_TABLE,
    INTAKE_REQUEST_TABLE,
    QUESTION_MATRIX_TABLE,
    ROLE_MATRIX_TABLE,
    db,
)

health_bp = Blueprint("health", __name__)


@health_bp.get("/healthz")
def healthz():
    return jsonify({"status": "ok"}), 200


@health_bp.get("/readyz")
def readyz():
    required_tables = [
        ROLE_MATRIX_TABLE,
        QUESTION_MATRIX_TABLE,
        ACTION_MATRIX_TABLE,
        INTAKE_REQUEST_TABLE,
    ]

    missing_tables: list[str] = []
    try:
        inspector = inspect(db.engine)
        existing = set(inspector.get_table_names())
        missing_tables = [table for table in required_tables if table not in existing]
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

    if missing_tables:
        return (
            jsonify(
                {
                    "status": "unready",
                    "guidance": "Run `flask db upgrade` or `alembic upgrade head`.",
                    "missing_tables": missing_tables,
                }
            ),
            503,
        )

    return jsonify({"status": "ready"}), 200
