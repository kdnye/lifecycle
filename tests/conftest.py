import pytest

from app import create_app
from app.auth_utils import SESSION_USER_ID_KEY
from app.models import User, db


@pytest.fixture(autouse=True)
def required_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide deterministic, test-safe env vars before app creation."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "test-postmark-token")
    monkeypatch.setenv("HR_CC_EMAILS", "hr-test@example.com")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("FSI_PRODUCTION", "false")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DEFAULT_SENDER_EMAIL", "no-reply@example.com")
    monkeypatch.setenv("MAIL_MESSAGE_STREAM", "outbound")
    monkeypatch.setenv("MAIL_SUPPRESS_SEND", "true")


@pytest.fixture
def app():
    flask_app = create_app()
    flask_app.config.update(
        TESTING=True,
        SERVER_NAME="localhost",
    )
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def create_user(app):
    """Factory fixture: creates and commits a User row in the test DB."""
    def _factory(email: str = "test@example.com", role: str = "EMPLOYEE", **kwargs):
        user = User(
            email=email,
            role=role,
            name=kwargs.pop("name", "Test User"),
        )
        for key, val in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, val)
        db.session.add(user)
        db.session.commit()
        return user

    return _factory


@pytest.fixture
def logged_in_client(client, create_user):
    """Returns (test_client, user) with an authenticated session injected."""
    user = create_user()
    with client.session_transaction() as sess:
        sess[SESSION_USER_ID_KEY] = user.id
    return client, user
