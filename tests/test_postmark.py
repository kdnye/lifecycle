import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import Mock, patch

from flask import Flask
import requests

from services.email import send_templated_email


def _make_app(**config_overrides):
    app = Flask(__name__)
    app.config.update(
        POSTMARK_SERVER_TOKEN="test-token",
        DEFAULT_SENDER_EMAIL="sender@example.com",
        MAIL_MESSAGE_STREAM="broadcast",
    )
    app.config.update(config_overrides)
    return app


@patch("services.email.requests.post")
def test_send_templated_email_success_with_cc(mock_post):
    app = _make_app()
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    with app.app_context():
        result = send_templated_email(
            to_email="employee@example.com",
            template_alias="welcome-template",
            template_model={"employee_name": "Pat"},
            cc_email="hr@example.com",
        )

    assert result is True
    mock_post.assert_called_once()

    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.postmarkapp.com/email/withTemplate"
    assert kwargs["headers"]["X-Postmark-Server-Token"] == "test-token"
    assert kwargs["json"] == {
        "From": "sender@example.com",
        "To": "employee@example.com",
        "TemplateAlias": "welcome-template",
        "TemplateModel": {"employee_name": "Pat"},
        "MessageStream": "broadcast",
        "Cc": "hr@example.com",
    }


@patch("services.email.requests.post")
def test_send_templated_email_success_without_cc(mock_post):
    app = _make_app()
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    with app.app_context():
        result = send_templated_email(
            to_email="employee@example.com",
            template_alias="welcome-template",
            template_model={"employee_name": "Pat"},
        )

    assert result is True
    payload = mock_post.call_args.kwargs["json"]
    assert payload["From"] == "sender@example.com"
    assert payload["To"] == "employee@example.com"
    assert payload["TemplateAlias"] == "welcome-template"
    assert payload["TemplateModel"] == {"employee_name": "Pat"}
    assert payload["MessageStream"] == "broadcast"
    assert "Cc" not in payload


@patch("services.email.requests.post")
def test_send_templated_email_returns_false_without_postmark_server_token(mock_post):
    app = _make_app(POSTMARK_SERVER_TOKEN=None)

    with app.app_context():
        result = send_templated_email(
            to_email="employee@example.com",
            template_alias="welcome-template",
            template_model={"employee_name": "Pat"},
        )

    assert result is False
    mock_post.assert_not_called()


@patch("services.email.requests.post")
def test_send_templated_email_returns_false_without_default_sender_email(mock_post):
    app = _make_app(DEFAULT_SENDER_EMAIL=None)

    with app.app_context():
        result = send_templated_email(
            to_email="employee@example.com",
            template_alias="welcome-template",
            template_model={"employee_name": "Pat"},
        )

    assert result is False
    mock_post.assert_not_called()


@patch("services.email.requests.post")
def test_send_templated_email_returns_false_on_request_exception(mock_post):
    app = _make_app()
    mock_post.side_effect = requests.RequestException("network error")

    with app.app_context():
        result = send_templated_email(
            to_email="employee@example.com",
            template_alias="welcome-template",
            template_model={"employee_name": "Pat"},
        )

    assert result is False


@patch("services.email.requests.post")
def test_send_templated_email_uses_explicit_message_stream_override(mock_post):
    app = _make_app(MAIL_MESSAGE_STREAM="broadcast")
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    with app.app_context():
        result = send_templated_email(
            to_email="employee@example.com",
            template_alias="welcome-template",
            template_model={"employee_name": "Pat"},
            message_stream="onboading",
        )

    assert result is True
    payload = mock_post.call_args.kwargs["json"]
    assert payload["MessageStream"] == "onboading"
