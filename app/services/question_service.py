from __future__ import annotations

import json
from typing import Optional

from app.models import IntakeAnswer, QuestionMatrix, db


def list_questions(
    active_only: bool = True,
    role_profile: Optional[str] = None,
    step: Optional[int] = None,
) -> list[QuestionMatrix]:
    q = QuestionMatrix.query
    if active_only:
        q = q.filter_by(is_active=True)
    if role_profile is not None:
        q = q.filter_by(role_profile=role_profile)
    if step is not None:
        q = q.filter_by(intake_step=step)
    return q.order_by(QuestionMatrix.intake_step, QuestionMatrix.sort_order).all()


def get_question(q_id: int) -> Optional[QuestionMatrix]:
    return db.session.get(QuestionMatrix, q_id)


def create_question(data: dict) -> QuestionMatrix:
    options = data.get("field_options")
    if options and not isinstance(options, str):
        options = json.dumps(options)
    q = QuestionMatrix(
        role_profile=data["role_profile"],
        question_key=data["question_key"],
        prompt=data["prompt"],
        is_required=bool(data.get("is_required", False)),
        field_type=data.get("field_type", "boolean"),
        field_options=options or None,
        intake_step=int(data.get("intake_step", 2)),
        sort_order=int(data.get("sort_order", 0)),
        is_active=True,
    )
    db.session.add(q)
    db.session.commit()
    return q


def update_question(q: QuestionMatrix, data: dict) -> QuestionMatrix:
    if "field_options" in data:
        opts = data["field_options"]
        if opts and not isinstance(opts, str):
            opts = json.dumps(opts)
        q.field_options = opts or None
    if "role_profile" in data:
        q.role_profile = data["role_profile"]
    if "question_key" in data:
        q.question_key = data["question_key"]
    if "prompt" in data:
        q.prompt = data["prompt"]
    if "is_required" in data:
        q.is_required = bool(data["is_required"])
    if "field_type" in data:
        q.field_type = data["field_type"]
    if "intake_step" in data:
        q.intake_step = int(data["intake_step"])
    if "sort_order" in data:
        q.sort_order = int(data["sort_order"])
    db.session.commit()
    return q


def deactivate_question(q: QuestionMatrix) -> None:
    q.is_active = False
    db.session.commit()


def delete_question(q: QuestionMatrix) -> None:
    db.session.delete(q)
    db.session.commit()


def reorder_questions(updates: list[dict]) -> None:
    for item in updates:
        q = db.session.get(QuestionMatrix, int(item["id"]))
        if q:
            q.sort_order = int(item["sort_order"])
            q.intake_step = int(item["intake_step"])
    db.session.commit()


def questions_by_step() -> dict[int, list[QuestionMatrix]]:
    """Returns active questions grouped by intake_step (keys 1-4), sorted by sort_order."""
    questions = list_questions(active_only=True)
    result: dict[int, list[QuestionMatrix]] = {1: [], 2: [], 3: [], 4: []}
    for q in questions:
        step = q.intake_step
        if step in result:
            result[step].append(q)
    return result


def save_answers(
    intake_request_id: int,
    payload: dict,
    questions: list[QuestionMatrix],
) -> None:
    """Persist dynamic question answers from an intake payload."""
    for q in questions:
        key = f"dynamic_{q.question_key}"
        value = payload.get(key)
        if value is None or str(value).strip() == "":
            continue
        answer = IntakeAnswer(
            intake_request_id=intake_request_id,
            question_id=q.id,
            question_key=q.question_key,
            answer_value=str(value).strip(),
        )
        db.session.add(answer)
    db.session.commit()
