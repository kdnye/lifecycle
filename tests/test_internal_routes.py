import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.models import IntakeRequest, db


def _build_db_test_client():
    app = create_app()
    app.config.update(TESTING=True, SERVER_NAME="localhost")
    with app.app_context():
        db.drop_all()
        db.create_all()
    return app.test_client(), app


def test_internal_cron_rejects_unauthenticated_calls(monkeypatch):
    monkeypatch.setenv("INTERNAL_CRON_SHARED_SECRET", "shared-secret")
    client, _ = _build_db_test_client()

    response = client.post("/api/internal/cron/process-terminations")

    assert response.status_code == 401
    assert response.get_json()["status"] == "error"


def test_internal_cron_processes_approved_and_skips_idempotent_records(monkeypatch):
    monkeypatch.setenv("INTERNAL_CRON_SHARED_SECRET", "shared-secret")
    client, app = _build_db_test_client()

    with app.app_context():
        approved = IntakeRequest(
            first_name="Approved",
            last_name="Worker",
            role_profile="office",
            event_type="offboarding",
            status="approved",
            termination_date=date.today(),
        )
        already_processed = IntakeRequest(
            first_name="Processed",
            last_name="Worker",
            role_profile="office",
            event_type="offboarding",
            status="processed",
            termination_date=date.today(),
        )
        rejected = IntakeRequest(
            first_name="Rejected",
            last_name="Worker",
            role_profile="office",
            event_type="offboarding",
            status="rejected",
            termination_date=date.today(),
        )
        pending = IntakeRequest(
            first_name="Pending",
            last_name="Worker",
            role_profile="office",
            event_type="offboarding",
            status="pending_approval",
            termination_date=date.today(),
        )
        db.session.add_all([approved, already_processed, rejected, pending])
        db.session.commit()

    def fake_execute(intake_id: int):
        with app.app_context():
            intake = db.session.get(IntakeRequest, intake_id)
            intake.status = "processed"
            db.session.commit()
        return {"status": "processed", "intake_id": intake_id, "tasks_generated": ["ok"]}

    monkeypatch.setattr("services.internal_automation.execute_lifecycle_event", fake_execute)

    response = client.post(
        "/api/internal/cron/process-terminations",
        headers={"X-FSI-Internal-Secret": "shared-secret"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["total_candidates"] == 4
    assert payload["processed"] == 1
    assert payload["skipped_final"] == 2
    assert payload["skipped_not_ready"] == 1


def test_internal_cron_auto_approves_hard_stop_contractors(monkeypatch):
    monkeypatch.setenv("INTERNAL_CRON_SHARED_SECRET", "shared-secret")
    client, app = _build_db_test_client()

    with app.app_context():
        contractor = IntakeRequest(
            first_name="Casey",
            last_name="Contractor",
            role_profile="contractor",
            event_type="offboarding",
            status="pending_approval",
            termination_date=date.today(),
        )
        db.session.add(contractor)
        db.session.commit()
        contractor_id = contractor.id

    def fake_execute(intake_id: int):
        with app.app_context():
            intake = db.session.get(IntakeRequest, intake_id)
            assert intake.status == "approved"
            intake.status = "processed"
            db.session.commit()
        return {"status": "processed", "intake_id": intake_id, "tasks_generated": ["ok"]}

    monkeypatch.setattr("services.internal_automation.execute_lifecycle_event", fake_execute)

    response = client.post(
        "/api/internal/cron/process-terminations",
        headers={"X-FSI-Internal-Secret": "shared-secret"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["auto_approved"] == 1
    assert payload["processed"] == 1

    with app.app_context():
        updated = db.session.get(IntakeRequest, contractor_id)
        assert updated.status == "processed"
