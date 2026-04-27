import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app


def test_create_app_uses_maintenance_mode_when_production_config_invalid(monkeypatch):
    monkeypatch.setenv("FSI_PRODUCTION", "true")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("POSTMARK_SERVER_TOKEN", raising=False)

    app = create_app()
    client = app.test_client()

    index_response = client.get("/")
    assert index_response.status_code == 503
    payload = index_response.get_json()
    assert payload["status"] == "maintenance"
    assert any("SECRET_KEY" in issue for issue in payload["issues"])
    assert any("DATABASE_URL" in issue for issue in payload["issues"])
    assert any("POSTMARK_SERVER_TOKEN" in issue for issue in payload["issues"])

    health_response = client.get("/healthz")
    assert health_response.status_code == 503
    assert health_response.get_json()["status"] == "unready"


def test_create_app_uses_maintenance_mode_when_postmark_token_missing(monkeypatch):
    monkeypatch.setenv("FSI_PRODUCTION", "true")
    monkeypatch.setenv("SECRET_KEY", "secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///lifecycle.db")
    monkeypatch.delenv("POSTMARK_SERVER_TOKEN", raising=False)

    app = create_app()
    client = app.test_client()

    index_response = client.get("/")
    assert index_response.status_code == 503
    payload = index_response.get_json()
    assert payload["status"] == "maintenance"
    assert any("POSTMARK_SERVER_TOKEN" in issue for issue in payload["issues"])

    health_response = client.get("/healthz")
    assert health_response.status_code == 503
    health_payload = health_response.get_json()
    assert health_payload["status"] == "unready"
    assert any("POSTMARK_SERVER_TOKEN" in issue for issue in health_payload["issues"])


def test_create_app_serves_requests_when_config_valid(monkeypatch):
    monkeypatch.setenv("FSI_PRODUCTION", "false")

    app = create_app()
    client = app.test_client()

    health_response = client.get("/healthz")
    assert health_response.status_code == 200
    assert health_response.get_json()["status"] == "ok"


def test_create_app_uses_maintenance_mode_when_database_url_is_malformed(monkeypatch):
    monkeypatch.setenv("FSI_PRODUCTION", "true")
    monkeypatch.setenv("SECRET_KEY", "secret")
    monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "token")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:abc/db")

    app = create_app()
    client = app.test_client()

    index_response = client.get("/")
    assert index_response.status_code == 503
    payload = index_response.get_json()
    assert payload["status"] == "maintenance"
    assert any("DATABASE_URL is malformed" in issue for issue in payload["issues"])
