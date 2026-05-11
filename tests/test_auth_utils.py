from flask import Blueprint, Flask

from app.auth_utils import login_required


def _build_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = "test-secret"

    auth_bp = Blueprint("auth", __name__)

    @auth_bp.route("/login")
    def login():
        return "login"

    app.register_blueprint(auth_bp, url_prefix="/auth")

    @app.route("/secure")
    @login_required
    def secure_page():
        return "ok"

    return app


def test_login_required_redirect_uses_relative_path_without_trailing_question_mark():
    app = _build_app()
    client = app.test_client()

    response = client.get("/secure", follow_redirects=False)

    assert response.status_code == 302
    location = response.headers["Location"]
    assert location.endswith("/auth/login?next=/secure")


def test_login_required_redirect_preserves_relative_query_string():
    app = _build_app()
    client = app.test_client()

    response = client.get("/secure?tab=details&mode=full", follow_redirects=False)

    assert response.status_code == 302
    location = response.headers["Location"]
    assert location.endswith("/auth/login?next=/secure?tab%3Ddetails%26mode%3Dfull")
