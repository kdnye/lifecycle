import sys
from pathlib import Path
from types import SimpleNamespace

from flask import Flask, g

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.blueprints.intake_builder.routes import intake_builder_bp


def _build_client(can_manage_lifecycle: bool = True):
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="test")

    @app.before_request
    def _attach_user():
        g.current_user = SimpleNamespace(can_manage_lifecycle=can_manage_lifecycle)

    app.register_blueprint(intake_builder_bp, url_prefix="/intake-builder")
    return app.test_client()


def test_board_requires_admin_access():
    client = _build_client(can_manage_lifecycle=False)
    response = client.get("/intake-builder/")
    assert response.status_code == 403


def test_reorder_questions_rejects_invalid_payload():
    client = _build_client(can_manage_lifecycle=True)
    response = client.post("/intake-builder/questions/reorder", json={"bad": []})
    assert response.status_code == 400
    assert "error" in response.get_json()
