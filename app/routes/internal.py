from __future__ import annotations

import secrets

from flask import Blueprint, abort, current_app, flash, g, jsonify, redirect, render_template, request, url_for

from app.services.hardware_review_service import (
    HardwareReviewValidationError,
    list_manual_review_requests,
    resolve_hardware_review,
)
from app.services.internal_automation import process_due_terminations


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
                    "remediation": "Set INTERNAL_CRON_SHARED_SECRET in environment/config before invoking this endpoint.",
                }
            ),
            503,
        )

    provided_secret = request.headers.get(_INTERNAL_SECRET_HEADER)
    if not _is_authorized(shared_secret, provided_secret):
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Unauthorized.",
                    "remediation": "Provide header X-FSI-Internal-Secret with the configured shared secret.",
                }
            ),
            401,
        )

    result = process_due_terminations()
    return jsonify(result), 200


def _require_internal_admin() -> None:
    user = getattr(g, "current_user", None)
    if user is None:
        abort(401)
    if not getattr(user, "can_manage_lifecycle", False):
        abort(403)


@internal_bp.get("/hardware-review")
def hardware_review():
    _require_internal_admin()
    requests = list_manual_review_requests()
    return render_template("internal/hardware_review.html", requests=requests)


@internal_bp.post("/hardware-review/resolve")
def resolve_hardware_review_route():
    _require_internal_admin()
    intake_request_id = request.form.get("intake_request_id", type=int)
    serial_number = request.form.get("serial_number", "")

    try:
        intake, _ = resolve_hardware_review(intake_request_id, serial_number)
    except HardwareReviewValidationError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("internal.hardware_review"))

    flash(f"Hardware provisioned for request #{intake.id}.", "success")
    return redirect(url_for("internal.hardware_review"))
