import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.models import AssetStatus, Inventory, db


def _build_db_test_client():
    app = create_app()
    app.config.update(TESTING=True, SERVER_NAME="localhost")
    with app.app_context():
        db.drop_all()
        db.create_all()
    return app.test_client(), app


def test_postmark_webhook_accepts_authorized_request_and_sets_available_status(monkeypatch):
    monkeypatch.setenv("POSTMARK_WEBHOOK_TOKEN", "webhook-secret")

    client, app = _build_db_test_client()

    response = client.post(
        "/api/webhooks/postmark-inbound",
        headers={"X-Postmark-Token": "webhook-secret"},
        json={
            "Subject": "Device Intake [RequestID: 42]",
            "TextBody": "Serial Number: SN-12345",
        },
    )

    assert response.status_code == 200
    with app.app_context():
        saved = Inventory.query.filter_by(serial_number="SN-12345").first()
        assert saved is not None
        assert saved.intake_request_id == 42
        assert saved.status == AssetStatus.AVAILABLE


def test_postmark_webhook_rejects_unauthorized_request(monkeypatch):
    monkeypatch.delenv("POSTMARK_WEBHOOK_TOKEN", raising=False)
    client, app = _build_db_test_client()
    app.config["FSI_PRODUCTION"] = True

    response = client.post(
        "/api/webhooks/postmark-inbound",
        headers={"X-Postmark-Token": "wrong-token"},
        json={"Subject": "Device Intake [RequestID: 9]", "TextBody": "Serial Number: SN-99999"},
    )

    assert response.status_code == 401


def test_postmark_webhook_ignores_payload_without_serial(monkeypatch):
    monkeypatch.setenv("POSTMARK_WEBHOOK_TOKEN", "webhook-secret")

    client, app = _build_db_test_client()

    response = client.post(
        "/api/webhooks/postmark-inbound",
        headers={"X-Postmark-Token": "webhook-secret"},
        json={"Subject": "Device Intake [RequestID: 15]", "TextBody": "No serial here."},
    )

    assert response.status_code == 200
    with app.app_context():
        assert Inventory.query.count() == 0


def test_postmark_webhook_handles_malformed_request_id_without_failing(monkeypatch):
    monkeypatch.setenv("POSTMARK_WEBHOOK_TOKEN", "webhook-secret")

    client, app = _build_db_test_client()

    response = client.post(
        "/api/webhooks/postmark-inbound",
        headers={"X-Postmark-Token": "webhook-secret"},
        json={"Subject": "Device Intake [RequestID: not-a-number]", "TextBody": "Serial Number: SN-77777"},
    )

    assert response.status_code == 200
    with app.app_context():
        saved = Inventory.query.filter_by(serial_number="SN-77777").first()
        assert saved is not None
        assert saved.intake_request_id is None


def test_postmark_webhook_treats_duplicate_serial_as_idempotent(monkeypatch):
    monkeypatch.setenv("POSTMARK_WEBHOOK_TOKEN", "webhook-secret")

    client, app = _build_db_test_client()
    payload = {"Subject": "Device Intake [RequestID: 3]", "TextBody": "Serial Number: SN-DUPL"}
    headers = {"X-Postmark-Token": "webhook-secret"}

    first = client.post("/api/webhooks/postmark-inbound", headers=headers, json=payload)
    second = client.post("/api/webhooks/postmark-inbound", headers=headers, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    with app.app_context():
        assert Inventory.query.filter_by(serial_number="SN-DUPL").count() == 1
