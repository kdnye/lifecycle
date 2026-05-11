from __future__ import annotations

import logging

import requests
from flask import current_app

POSTMARK_SEND_WITH_TEMPLATE_URL = "https://api.postmarkapp.com/email/withTemplate"

logger = logging.getLogger(__name__)


def send_templated_email(
    to_email: str,
    template_alias: str,
    template_model: dict,
    cc_email: str | None = None,
    message_stream: str | None = None,
) -> bool:
    """Send a Postmark templated transactional email."""
    server_token = current_app.config.get("POSTMARK_SERVER_TOKEN")
    sender = current_app.config.get("DEFAULT_SENDER_EMAIL")
    resolved_message_stream = message_stream or current_app.config.get("MAIL_MESSAGE_STREAM", "outbound")

    if current_app.config.get("MAIL_SUPPRESS_SEND"):
        logger.info(
            "mail_suppressed template=%s to=%s",
            template_alias,
            to_email,
        )
        return True

    if not server_token:
        logger.error("POSTMARK_SERVER_TOKEN is not configured.")
        return False
    if not sender:
        logger.error("DEFAULT_SENDER_EMAIL is not configured.")
        return False

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Postmark-Server-Token": server_token,
    }
    payload = {
        "From": sender,
        "To": to_email,
        "TemplateAlias": template_alias,
        "TemplateModel": template_model,
        "MessageStream": resolved_message_stream,
    }
    if cc_email:
        payload["Cc"] = cc_email

    try:
        response = requests.post(
            POSTMARK_SEND_WITH_TEMPLATE_URL,
            headers=headers,
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception(
            "Failed Postmark send for template alias '%s' to '%s'.",
            template_alias,
            to_email,
        )
        return False
