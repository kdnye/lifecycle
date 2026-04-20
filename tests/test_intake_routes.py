import sys
from pathlib import Path

from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routes.intake import intake_bp


def _build_test_client():
    app = Flask(__name__)
    app.register_blueprint(intake_bp)
    app.config["TESTING"] = True
    return app.test_client()


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
