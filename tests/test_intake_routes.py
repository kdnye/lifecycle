import sys
from pathlib import Path

from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.models import IntakeRequest, db
from app.routes.intake import intake_bp
from services.intake_dispatch import process_intake_dispatch
from services.workflow import execute_lifecycle_event


def _build_test_client():
    app = Flask(__name__)
    app.register_blueprint(intake_bp)
    app.config["TESTING"] = True
    return app.test_client()


def _build_db_test_client():
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
