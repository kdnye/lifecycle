from flask import (
    Blueprint,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.auth_utils import login_required
from app.models import User
from app.services import question_service

intake_builder_bp = Blueprint("intake_builder", __name__)


def _require_admin() -> None:
    user = db_get_user()
    if not user or not user.can_manage_lifecycle:
        abort(403)


def db_get_user():
    from app.models import db
    return db.session.get(User, session.get("fsi_user_id"))


@intake_builder_bp.get("/")
@login_required
def board():
    _require_admin()
    step_questions = question_service.questions_by_step()
    return render_template("intake_builder/board.html", step_questions=step_questions)


@intake_builder_bp.post("/questions")
@login_required
def create_question():
    _require_admin()
    data = request.form.to_dict()
    data["is_required"] = "is_required" in request.form
    question_service.create_question(data)
    return redirect(url_for("intake_builder.board"))


@intake_builder_bp.get("/questions/<int:q_id>/edit")
@login_required
def edit_question_form(q_id: int):
    _require_admin()
    q = question_service.get_question(q_id)
    if q is None:
        abort(404)
    return render_template("intake_builder/edit.html", question=q)


@intake_builder_bp.post("/questions/<int:q_id>/edit")
@login_required
def update_question(q_id: int):
    _require_admin()
    q = question_service.get_question(q_id)
    if q is None:
        abort(404)
    data = request.form.to_dict()
    data["is_required"] = "is_required" in request.form
    question_service.update_question(q, data)
    return redirect(url_for("intake_builder.board"))


@intake_builder_bp.post("/questions/<int:q_id>/delete")
@login_required
def delete_question(q_id: int):
    _require_admin()
    q = question_service.get_question(q_id)
    if q is None:
        abort(404)
    question_service.deactivate_question(q)
    return redirect(url_for("intake_builder.board"))


@intake_builder_bp.post("/questions/reorder")
@login_required
def reorder_questions():
    _require_admin()
    body = request.get_json(silent=True) or {}
    updates = body.get("updates", [])
    question_service.reorder_questions(updates)
    return "", 204
