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


def _login_manager(app, email: str = "admin@example.com"):
    from app.auth_utils import set_authenticated_user
    from app.models import User

    with app.app_context():
        user = User(email=email, can_manage_lifecycle=True, auth_provider="local", role="ADMIN")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    with app.test_request_context():
        pass

    return user_id


def test_hardware_review_requires_admin_session():
    client, _ = _build_db_test_client()

    response = client.get("/api/internal/hardware-review")

    assert response.status_code == 401


def test_hardware_review_lists_manual_review_requests():
    client, app = _build_db_test_client()

    with app.app_context():
        db.session.add_all([
            IntakeRequest(first_name="A", last_name="One", role_profile="office", event_type="onboarding", status="Needs Manual Review"),
            IntakeRequest(first_name="B", last_name="Two", role_profile="office", event_type="onboarding", status="approved"),
        ])
        from app.models import User

        user = User(email="manager@example.com", can_manage_lifecycle=True, auth_provider="local", role="ADMIN")
        user.set_password("pw")
        db.session.add(user)
        db.session.commit()
        uid = user.id

    with client.session_transaction() as sess:
        sess["fsi_user_id"] = uid

    response = client.get("/api/internal/hardware-review")

    assert response.status_code == 200
    assert b"Hardware Review" in response.data
    assert b"#1" in response.data
    assert b"#2" not in response.data


def test_hardware_review_resolve_validates_and_flashes_error():
    client, app = _build_db_test_client()

    with app.app_context():
        req = IntakeRequest(first_name="A", last_name="One", role_profile="office", event_type="onboarding", status="Needs Manual Review")
        from app.models import User

        user = User(email="manager2@example.com", can_manage_lifecycle=True, auth_provider="local", role="ADMIN")
        user.set_password("pw")
        db.session.add_all([req, user])
        db.session.commit()
        uid = user.id

    with client.session_transaction() as sess:
        sess["fsi_user_id"] = uid

    response = client.post(
        "/api/internal/hardware-review/resolve",
        data={"intake_request_id": 1, "serial_number": ""},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Serial number is required." in response.data


def test_hardware_review_resolve_updates_inventory_and_status():
    client, app = _build_db_test_client()

    with app.app_context():
        req = IntakeRequest(first_name="A", last_name="One", role_profile="office", event_type="onboarding", status="Needs Manual Review")
        from app.models import Inventory, User

        user = User(email="manager3@example.com", can_manage_lifecycle=True, auth_provider="local", role="ADMIN")
        user.set_password("pw")
        db.session.add_all([req, user])
        db.session.commit()
        uid = user.id
        req_id = req.id

    with client.session_transaction() as sess:
        sess["fsi_user_id"] = uid

    response = client.post(
        "/api/internal/hardware-review/resolve",
        data={"intake_request_id": req_id, "serial_number": " ab-123 !! "},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Hardware provisioned for request" in response.data

    with app.app_context():
        from app.models import Inventory

        updated = db.session.get(IntakeRequest, req_id)
        linked = db.session.query(Inventory).filter(Inventory.intake_request_id == req_id).one()
        assert updated.status == "Hardware Provisioned"
        assert linked.serial_number == "AB-123"
