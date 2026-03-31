from flask import Blueprint, jsonify, render_template, request

from services.workflow import IntakeContext, build_action_plan, process_onboarding_request

intake_bp = Blueprint("intake", __name__)


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
    intake_id = payload.get("intake_id")

    if not isinstance(intake_id, int):
        return jsonify({"status": "error", "message": "`intake_id` (int) is required."}), 400

    result = process_onboarding_request(intake_id)
    status_code = 200 if result.get("status") == "processed" else 400
    return jsonify(result), status_code
