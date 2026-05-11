import sys
import os
from pathlib import Path

from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.models import IntakeAnswer, IntakeRequest, QuestionMatrix, db
from app.routes.intake import intake_bp
from services.intake_dispatch import process_intake_dispatch
from services.workflow import execute_lifecycle_event


def _build_test_client():
    app = Flask(__name__)
    app.register_blueprint(intake_bp)
    app.config["TESTING"] = True
    return app.test_client()


def _build_db_test_client():
    os.environ["DATABASE_URL"] = "sqlite:////tmp/lifecycle_test_intake.db"
    app = create_app()
    app.config.update(TESTING=True, SERVER_NAME="localhost")
    with app.app_context():
        db.drop_all()
        db.create_all()
    return app.test_client(), app


def test_process_returns_structured_400_for_missing_json_body():
    client = _build_test_client()

    response = client.post("/intake/process")

    assert response.status_code == 400
    assert response.get_json()["status"] == "error"
    assert response.get_json()["message"] == "Missing required fields."


def test_process_returns_structured_400_for_incomplete_payload():
    client = _build_test_client()

    response = client.post("/intake/process", json={"first_name": "Ada"})

    assert response.status_code == 400
    assert response.get_json()["status"] == "error"
    assert response.get_json()["message"] == "Missing required fields."


def test_process_intake_dispatch_transitions_draft_to_pending_approval(monkeypatch):
    client, app = _build_db_test_client()

    def fake_initiate_lifecycle_event(intake_id):
        with app.app_context():
            intake = db.session.get(IntakeRequest, intake_id)
            assert intake is not None
            assert intake.status == "draft"
            intake.status = "pending_approval"
            db.session.commit()
        return {"status": "pending_approval", "intake_id": intake_id}

    monkeypatch.setattr("services.intake_dispatch.initiate_lifecycle_event", fake_initiate_lifecycle_event)

    with app.app_context():
        result = process_intake_dispatch(
            {
                "status": "draft",
                "event_type": "onboarding",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "start_date": "2026-05-01",
                "role_profile": "office",
                "manager_email": "manager@example.com",
            }
        )

        intake = IntakeRequest.query.order_by(IntakeRequest.id.desc()).first()
        assert intake is not None
        assert intake.status == "pending_approval"
        assert result.status_code == 202
        assert result.body["status"] == "pending_approval"


def test_offboarding_waits_for_approval_before_execution(monkeypatch):
    client, app = _build_db_test_client()
    monkeypatch.setattr("services.workflow.send_templated_email", lambda **_: True)
    monkeypatch.setattr("services.workflow._execute_offboarding", lambda intake: ["Offboarding processed"])

    payload = {
        "status": "submitted",
        "event_type": "offboarding",
        "first_name": "Grace",
        "last_name": "Hopper",
        "start_date": "2026-05-02",
        "role_profile": "office",
        "manager_email": "manager@example.com",
    }
    create_response = client.post("/intake/process", json=payload)
    assert create_response.status_code == 202
    assert create_response.get_json()["status"] == "pending_approval"

    with app.app_context():
        intake = IntakeRequest.query.order_by(IntakeRequest.id.desc()).first()
        assert intake is not None
        assert intake.status == "pending_approval"
        preapproval_result = execute_lifecycle_event(intake.id)
        assert preapproval_result["status"] == "error"
        assert preapproval_result["message"] == "Event not approved for execution."
        token = intake.approval_token

    approve_response = client.get(f"/intake/approve/{token}")
    assert approve_response.status_code == 200
    assert b"Approved and processed" in approve_response.data

    with app.app_context():
        updated = IntakeRequest.query.filter_by(approval_token=token).first()
        assert updated is not None
        assert updated.status == "processed"


def test_intake_form_context_includes_step_questions():
    client, app = _build_db_test_client()
    with app.app_context():
        db.session.add(
            QuestionMatrix(
                role_profile="office",
                question_key="office_needs_badge",
                prompt="Needs badge?",
                intake_step=2,
                sort_order=5,
                is_active=True,
            )
        )
        db.session.commit()

    response = client.get("/intake/")
    assert response.status_code == 200
    assert b"Needs badge?" in response.data


def test_process_persists_dynamic_answers_to_intake_answer(monkeypatch):
    client, app = _build_db_test_client()
    monkeypatch.setattr("services.workflow.send_templated_email", lambda **_: True)

    with app.app_context():
        question = QuestionMatrix(
            role_profile="office",
            question_key="needs_special_access",
            prompt="Needs special access?",
            intake_step=1,
            sort_order=1,
            is_active=True,
        )
        db.session.add(question)
        db.session.commit()
        question_id = question.id

    payload = {
        "status": "submitted",
        "event_type": "onboarding",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "start_date": "2026-05-02",
        "role_profile": "office",
        "manager_email": "manager@example.com",
        "dynamic_needs_special_access": " yes ",
    }
    response = client.post("/intake/process", json=payload)
    assert response.status_code == 202

    with app.app_context():
        intake = IntakeRequest.query.order_by(IntakeRequest.id.desc()).first()
        assert intake is not None
        answers = IntakeAnswer.query.filter_by(intake_request_id=intake.id).all()
        assert len(answers) == 1
        assert answers[0].question_matrix_id == question_id
        assert answers[0].answer_value == "yes"
