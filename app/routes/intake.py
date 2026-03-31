from flask import Blueprint, jsonify, render_template, request

from services.workflow import IntakeContext, build_action_plan

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
