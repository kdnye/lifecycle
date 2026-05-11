from __future__ import annotations

from collections import defaultdict

from app.models import QuestionMatrix


def get_grouped_active_questions_by_step() -> dict[int, list[QuestionMatrix]]:
    """Return active dynamic intake questions grouped by intake step."""
    questions = (
        QuestionMatrix.query.filter_by(is_active=True, is_dynamic=True)
        .order_by(QuestionMatrix.intake_step.asc(), QuestionMatrix.sort_order.asc(), QuestionMatrix.id.asc())
        .all()
    )

    grouped: dict[int, list[QuestionMatrix]] = defaultdict(list)
    for question in questions:
        grouped[question.intake_step].append(question)

    return dict(grouped)
