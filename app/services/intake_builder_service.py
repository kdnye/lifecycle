from __future__ import annotations

from app.models import QuestionMatrix, db


def list_questions() -> list[QuestionMatrix]:
    return (
        db.session.query(QuestionMatrix)
        .order_by(QuestionMatrix.intake_step.asc(), QuestionMatrix.sort_order.asc(), QuestionMatrix.id.asc())
        .all()
    )


def create_question(payload: dict) -> QuestionMatrix:
    question = QuestionMatrix(
        role_profile=(payload.get("role_profile") or "").strip(),
        question_key=(payload.get("question_key") or "").strip(),
        prompt=(payload.get("prompt") or "").strip(),
        is_required=bool(payload.get("is_required")),
        intake_step=int(payload.get("intake_step") or 1),
        field_type=(payload.get("field_type") or "text").strip() or "text",
        options_json=(payload.get("options_json") or "").strip() or None,
        depends_on_question_key=(payload.get("depends_on_question_key") or "").strip() or None,
        depends_on_answer_value=(payload.get("depends_on_answer_value") or "").strip() or None,
        visibility_rule=(payload.get("visibility_rule") or "equals").strip() or "equals",
        is_dynamic=bool(payload.get("is_dynamic")),
        sort_order=int(payload.get("sort_order") or 0),
        is_active=bool(payload.get("is_active", True)),
    )
    db.session.add(question)
    db.session.commit()
    return question


def get_question(question_id: int) -> QuestionMatrix | None:
    return db.session.get(QuestionMatrix, question_id)


def update_question(question: QuestionMatrix, payload: dict) -> QuestionMatrix:
    question.role_profile = (payload.get("role_profile") or "").strip()
    question.question_key = (payload.get("question_key") or "").strip()
    question.prompt = (payload.get("prompt") or "").strip()
    question.is_required = bool(payload.get("is_required"))
    question.intake_step = int(payload.get("intake_step") or 1)
    question.field_type = (payload.get("field_type") or "text").strip() or "text"
    question.options_json = (payload.get("options_json") or "").strip() or None
    question.depends_on_question_key = (payload.get("depends_on_question_key") or "").strip() or None
    question.depends_on_answer_value = (payload.get("depends_on_answer_value") or "").strip() or None
    question.visibility_rule = (payload.get("visibility_rule") or "equals").strip() or "equals"
    question.is_dynamic = bool(payload.get("is_dynamic"))
    question.sort_order = int(payload.get("sort_order") or 0)
    question.is_active = bool(payload.get("is_active"))
    db.session.commit()
    return question


def delete_question(question: QuestionMatrix) -> None:
    db.session.delete(question)
    db.session.commit()


def reorder_questions(updates: list[dict]) -> None:
    for item in updates:
        question_id = item.get("id")
        if question_id is None:
            continue
        question = db.session.get(QuestionMatrix, int(question_id))
        if question is None:
            continue
        if "sort_order" in item:
            question.sort_order = int(item.get("sort_order") or 0)
        if "intake_step" in item:
            question.intake_step = int(item.get("intake_step") or question.intake_step)
    db.session.commit()
