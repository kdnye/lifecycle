import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import IntakeAnswer, IntakeRequest, QuestionMatrix, db
from app.services.question_service import get_grouped_active_questions_by_step, save_answers
from app import create_app


def _build_app():
    os.environ["DATABASE_URL"] = "sqlite:////tmp/lifecycle_test_questions.db"
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.drop_all()
        db.create_all()
    return app


def test_get_grouped_active_questions_by_step_sorts_and_filters_active():
    app = _build_app()
    with app.app_context():
        q1 = QuestionMatrix(
            role_profile="office",
            question_key="q_step2",
            prompt="Step 2",
            intake_step=2,
            sort_order=10,
            is_active=True,
        )
        q2 = QuestionMatrix(
            role_profile="office",
            question_key="q_step1_first",
            prompt="Step 1 First",
            intake_step=1,
            sort_order=1,
            is_active=True,
        )
        q3 = QuestionMatrix(
            role_profile="office",
            question_key="q_step1_second",
            prompt="Step 1 Second",
            intake_step=1,
            sort_order=2,
            is_active=True,
        )
        q_inactive = QuestionMatrix(
            role_profile="office",
            question_key="q_inactive",
            prompt="Inactive",
            intake_step=1,
            sort_order=0,
            is_active=False,
        )
        db.session.add_all([q1, q2, q3, q_inactive])
        db.session.commit()

        grouped = get_grouped_active_questions_by_step()
        assert list(grouped.keys()) == [1, 2]
        assert [q.question_key for q in grouped[1]] == ["q_step1_first", "q_step1_second"]
        assert [q.question_key for q in grouped[2]] == ["q_step2"]


def test_save_answers_persists_dynamic_payload_keys():
    app = _build_app()
    with app.app_context():
        intake = IntakeRequest(
            first_name="Ada",
            last_name="Lovelace",
            role_profile="office",
            event_type="onboarding",
            manager_email="manager@example.com",
            status="draft",
        )
        question = QuestionMatrix(
            role_profile="office",
            question_key="needs_special_access",
            prompt="Needs special access?",
            is_active=True,
        )
        db.session.add_all([intake, question])
        db.session.commit()

        saved_count = save_answers(
            intake.id,
            {
                "dynamic_needs_special_access": " yes ",
                "dynamic_unknown": "ignored",
            },
        )
        db.session.commit()

        assert saved_count == 1
        rows = IntakeAnswer.query.filter_by(intake_request_id=intake.id).all()
        assert len(rows) == 1
        assert rows[0].question_matrix_id == question.id
        assert rows[0].answer_value == "yes"
