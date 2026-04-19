from datetime import datetime

from flask import Blueprint, jsonify, render_template, request

from app.models import IntakeRequest, db
from services.workflow import (
    IntakeContext,
    build_action_plan,
    execute_lifecycle_event,
    initiate_lifecycle_event,
)

intake_bp = Blueprint("intake", __name__)

TRUTHY_CHECKBOX_VALUES = {"1", "true", "on", "yes"}


def _to_bool(value: object) -> bool:
    return str(value).strip().lower() in TRUTHY_CHECKBOX_VALUES


def _parse_optional_iso_date(value: str | None):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


@intake_bp.get("/")
def intake_form():
    return render_template("intake/form.html")


@intake_bp.post("/preview-actions")
def preview_actions():
    payload = request.get_json(silent=True) or {}
    context = IntakeContext(
        employee_name=payload.get("employee_name", ""),
        role_profile=payload.get("role_profile", "office"),
        event_type=payload.get("event_type", "onboarding"),
        manager_name=payload.get("manager_name"),
    )
    return jsonify({"actions": build_action_plan(context)})


@intake_bp.post("/process")
def process_intake():
    payload = request.get_json(silent=True) or {}

    required_fields = ["first_name", "last_name", "role_profile", "event_type"]
    if not all(payload.get(field) for field in required_fields):
        return jsonify({"status": "error", "message": "Missing required fields."}), 400

    try:
        termination_date = _parse_optional_iso_date(payload.get("termination_date"))
    except ValueError:
        return jsonify({"status": "error", "message": "termination_date must use YYYY-MM-DD format."}), 400

    new_request = IntakeRequest(
        first_name=payload["first_name"].strip(),
        last_name=payload["last_name"].strip(),
        role_profile=payload["role_profile"],
        event_type=payload["event_type"],
        manager_email=payload.get("manager_email", "").strip() or None,
        driver_needs_laptop=_to_bool(payload.get("driver_needs_laptop")),
        driver_needs_printer=_to_bool(payload.get("driver_needs_printer")),
        driver_needs_fuel_card=_to_bool(payload.get("driver_needs_fuel_card")),
        driver_needs_vehicle=_to_bool(payload.get("driver_needs_vehicle")),
        termination_date=termination_date,
        is_immediate=_to_bool(payload.get("is_immediate")),
        forwarding_email=payload.get("forwarding_email", "").strip() or None,
        status="draft",
    )
    db.session.add(new_request)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Unable to create intake request."}), 500

    result = initiate_lifecycle_event(new_request.id)
    status_code = 200 if result.get("status") in {"pending_approval", "pending"} else 400
    return jsonify(result), status_code


@intake_bp.route("/approve/<token>", methods=["GET"])
def approve_request(token):
    intake_request = IntakeRequest.query.filter_by(approval_token=token).first_or_404()

    if intake_request.status != "pending_approval":
        return render_template(
            "auth/message.html",
            message="This request has already been processed.",
            tasks=[],
        )

    intake_request.status = "approved"
    db.session.commit()
    result = execute_lifecycle_event(intake_request.id)

    if result.get("status") == "processed":
        return render_template(
            "auth/message.html",
            message=f"Success. Lifecycle event for {intake_request.first_name} is processing.",
            tasks=result.get("tasks_generated", []),
        )

    return render_template(
        "auth/message.html",
        message=f"Approval recorded but execution failed: {result.get('message', 'Unknown error')}",
        tasks=[],
    )


@intake_bp.route("/reject/<token>", methods=["GET"])
def reject_request(token):
    intake_request = IntakeRequest.query.filter_by(approval_token=token).first_or_404()
    intake_request.status = "rejected"
    db.session.commit()
    return render_template(
        "auth/message.html",
        message="Request rejected. No MSP tickets were generated.",
        tasks=[],
    )
