from flask import Blueprint, jsonify, render_template, request

from app.models import IntakeRequest, db
from services.workflow import IntakeContext, build_action_plan, process_onboarding_request

intake_bp = Blueprint("intake", __name__)

TRUTHY_CHECKBOX_VALUES = {"1", "true", "on", "yes"}


def _to_bool(value: object) -> bool:
    return str(value).strip().lower() in TRUTHY_CHECKBOX_VALUES


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


@intake_bp.post("/process-onboarding")
def process_onboarding():
    payload = request.get_json(silent=True) or {}

    required_fields = ["first_name", "last_name", "role_profile", "event_type"]
    if not all(payload.get(field) for field in required_fields):
        return jsonify({"status": "error", "message": "Missing required fields."}), 400

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
        status="processing",
    )
    db.session.add(new_request)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Unable to create intake request."}), 500

    if new_request.event_type == "onboarding":
        result = process_onboarding_request(new_request.id)
    else:
        result = {
            "status": "pending",
            "message": "Offboarding logic not yet implemented.",
            "intake_id": new_request.id,
        }

    status_code = 200 if result.get("status") in {"processed", "pending"} else 400
    return jsonify(result), status_code
