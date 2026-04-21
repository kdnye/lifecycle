import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import load_settings, validate_production_settings


def test_load_settings_uses_database_url_when_provided(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASS", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("INSTANCE_CONNECTION_NAME", raising=False)

    settings = load_settings()

    assert settings.database_url == "postgresql://user:pass@localhost/db"


def test_load_settings_builds_cloud_sql_url_from_component_vars(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_USER", "service-user")
    monkeypatch.setenv("DB_PASS", "p@ss word")
    monkeypatch.setenv("DB_NAME", "lifecycle")
    monkeypatch.setenv("INSTANCE_CONNECTION_NAME", "my-project:us-central1:lifecycle-db")

    settings = load_settings()

    assert (
        settings.database_url
        == "postgresql+pg8000://service-user:p%40ss+word@/lifecycle"
        "?unix_sock=/cloudsql/my-project:us-central1:lifecycle-db/.s.PGSQL.5432"
    )


def test_load_settings_treats_cloud_run_as_production_when_flag_missing(monkeypatch):
    monkeypatch.delenv("FSI_PRODUCTION", raising=False)
    monkeypatch.setenv("K_SERVICE", "lifecycle-service")

    settings = load_settings()

    assert settings.fsi_production is True


def test_validate_production_settings_requires_postgres_database_url(monkeypatch):
    monkeypatch.setenv("FSI_PRODUCTION", "true")
    monkeypatch.setenv("SECRET_KEY", "secret")
    monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "token")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///lifecycle.db")

    settings = load_settings()
    issues = validate_production_settings(settings)

    assert (
        "DATABASE_URL must be PostgreSQL in production (expected postgresql:// or postgresql+driver://)."
        in issues
    )
