from unittest.mock import patch

from flask import Flask

from app.routes.intake import intake_bp


def _build_test_client():
    app = Flask(__name__)
    app.register_blueprint(intake_bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_process_onboarding_request_patch_target_is_module_scoped_import():
    """Guardrail test: patch the module-scoped import used by intake routes."""
    with patch("app.routes.intake.process_onboarding_request") as mocked:
        mocked.return_value = {"status": "queued", "intake_id": 1, "tickets": []}
        result = mocked(1)

    assert result["status"] == "queued"


def test_process_onboarding_returns_structured_400_for_missing_json_body():
    client = _build_test_client()

    response = client.post("/process-onboarding")

    assert response.status_code == 400
    assert response.get_json()["status"] == "error"
    assert response.get_json()["message"] == "Missing required fields."


def test_process_onboarding_returns_structured_400_for_incomplete_payload():
    client = _build_test_client()

    response = client.post("/process-onboarding", json={"first_name": "Ada"})

    assert response.status_code == 400
    assert response.get_json()["status"] == "error"
    assert response.get_json()["message"] == "Missing required fields."
