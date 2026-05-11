import sys
from pathlib import Path
from types import SimpleNamespace

from flask import Flask, g

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.blueprints.permissions.routes import permissions_bp


def _build_client(can_manage_lifecycle: bool = True):
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="test")

    @app.before_request
    def _attach_user():
        g.current_user = SimpleNamespace(can_manage_lifecycle=can_manage_lifecycle)

    app.register_blueprint(permissions_bp, url_prefix="/permissions")
    return app.test_client()


def test_permissions_routes_require_admin():
    client = _build_client(can_manage_lifecycle=False)
    response = client.get("/permissions/matrix")
    assert response.status_code == 403


def test_permissions_route_requires_authenticated_user():
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY="test")
    app.register_blueprint(permissions_bp, url_prefix="/permissions")
    client = app.test_client()
    response = client.get("/permissions/matrix")
    assert response.status_code == 401
