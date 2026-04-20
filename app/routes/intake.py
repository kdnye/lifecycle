from flask import Blueprint, jsonify, render_template, request

from app.models import IntakeRequest, db
from services.intake_dispatch import process_intake_dispatch
from services.workflow import execute_lifecycle_event

intake_bp = Blueprint("intake", __name__, url_prefix="/intake")


@intake_bp.get("/")
def intake_form():
    return render_template("intake/form.html")


@intake_bp.post("/process")
def process_intake():
    result = process_intake_dispatch(request.get_json(silent=True) or {})
    return jsonify(result.body), result.status_code


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
