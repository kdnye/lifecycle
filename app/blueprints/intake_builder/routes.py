from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for

from app.services import intake_builder_service


intake_builder_bp = Blueprint("intake_builder", __name__)


def _require_admin() -> None:
    user = getattr(g, "current_user", None)
    if user is None:
        abort(401)
    if not getattr(user, "can_manage_lifecycle", False):
        abort(403)


@intake_builder_bp.get("/")
def board():
    _require_admin()
    questions = intake_builder_service.list_questions()
    return render_template("intake_builder/board.html", questions=questions)


@intake_builder_bp.post("/questions")
def create_question():
    _require_admin()
    intake_builder_service.create_question(request.form)
    flash("Question created.", "success")
    return redirect(url_for("intake_builder.board"))


@intake_builder_bp.route("/questions/<int:question_id>/edit", methods=["GET", "POST"])
def edit_question(question_id: int):
    _require_admin()
    question = intake_builder_service.get_question(question_id)
    if question is None:
        abort(404)

    if request.method == "POST":
        intake_builder_service.update_question(question, request.form)
        flash("Question updated.", "success")
        return redirect(url_for("intake_builder.board"))

    return render_template("intake_builder/edit.html", question=question)


@intake_builder_bp.post("/questions/<int:question_id>/delete")
def delete_question(question_id: int):
    _require_admin()
    question = intake_builder_service.get_question(question_id)
    if question is None:
        abort(404)
    intake_builder_service.delete_question(question)
    flash("Question deleted.", "success")
    return redirect(url_for("intake_builder.board"))


@intake_builder_bp.post("/questions/reorder")
def reorder_questions():
    _require_admin()
    payload = request.get_json(silent=True) or {}
    updates = payload.get("updates")
    if not isinstance(updates, list):
        return jsonify({"error": "Invalid payload. Expected {'updates': [...]}"}), 400
    intake_builder_service.reorder_questions(updates)
    return ("", 204)
