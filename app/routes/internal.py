from __future__ import annotations

import secrets

from flask import Blueprint, current_app, jsonify, request

from services.internal_automation import process_due_terminations


internal_bp = Blueprint("internal", __name__, url_prefix="/api/internal")
_INTERNAL_SECRET_HEADER = "X-FSI-Internal-Secret"


def _is_authorized(shared_secret: str | None, provided_secret: str | None) -> bool:
    if not shared_secret:
        return False
    return secrets.compare_digest(shared_secret, (provided_secret or ""))


@internal_bp.post("/cron/process-terminations")
def process_terminations_cron():
    shared_secret = current_app.config.get("INTERNAL_CRON_SHARED_SECRET")
    if not shared_secret:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "INTERNAL_CRON_SHARED_SECRET is not configured.",
                }
            ),
            503,
        )

    provided_secret = request.headers.get(_INTERNAL_SECRET_HEADER)
    if not _is_authorized(shared_secret, provided_secret):
        return jsonify({"status": "error", "message": "Unauthorized."}), 401

    result = process_due_terminations()
    return jsonify(result), 200
