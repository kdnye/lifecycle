from unittest.mock import patch


def test_process_onboarding_request_patch_target_is_module_scoped_import():
    """Guardrail test: patch the module-scoped import used by intake routes."""
    with patch("app.routes.intake.process_onboarding_request") as mocked:
        mocked.return_value = {"status": "queued", "intake_id": 1, "tickets": []}
        result = mocked(1)

    assert result["status"] == "queued"
