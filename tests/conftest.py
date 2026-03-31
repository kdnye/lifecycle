import pytest


@pytest.fixture(autouse=True)
def required_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide deterministic, test-safe env vars before app creation."""
    # Required by app config/services
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "test-postmark-token")
    monkeypatch.setenv("HR_CC_EMAILS", "hr-test@example.com")

    # Test-safe defaults
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("FSI_PRODUCTION", "false")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DEFAULT_SENDER_EMAIL", "no-reply@example.com")
    monkeypatch.setenv("MAIL_MESSAGE_STREAM", "outbound")
