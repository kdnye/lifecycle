from __future__ import annotations

from collections.abc import Mapping

from app.models import IntakeAnswer, QuestionMatrix, db


class AnswerPersistenceError(RuntimeError):
    """Raised when dynamic intake answers cannot be persisted safely."""


def save_answers(intake_request_id: int, payload: Mapping[str, object]) -> int:
    """Persist dynamic intake answers for active questions.

    Expected payload keys follow the pattern ``dynamic_<question_key>``.
    Blank and null-ish values are ignored.

    Returns the number of persisted answers.
    """

    active_questions = (
        db.session.query(QuestionMatrix)
        .filter(QuestionMatrix.is_active.is_(True))
        .all()
    )

    answers_to_save: list[IntakeAnswer] = []

    for question in active_questions:
        payload_key = f"dynamic_{question.question_key}"
        if payload_key not in payload:
            continue

        raw_value = payload.get(payload_key)
        if raw_value is None:
            continue

        if isinstance(raw_value, str):
            answer_value = raw_value.strip()
            if not answer_value:
                continue
        else:
            answer_value = str(raw_value).strip()
            if not answer_value:
                continue

        answers_to_save.append(
            IntakeAnswer(
                intake_request_id=intake_request_id,
                question_matrix_id=question.id,
                answer_value=answer_value,
            )
        )

    if not answers_to_save:
        return 0

    try:
        with db.session.begin_nested():
            db.session.add_all(answers_to_save)
            db.session.flush()
    except Exception as exc:  # noqa: BLE001 - normalize service-layer failures
        raise AnswerPersistenceError(
            "Failed to persist intake answers for dynamic question payload."
        ) from exc

    return len(answers_to_save)
