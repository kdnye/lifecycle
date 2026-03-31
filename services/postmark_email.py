from dataclasses import dataclass

import requests


POSTMARK_SEND_WITH_TEMPLATE_URL = "https://api.postmarkapp.com/email/withTemplate"


@dataclass(frozen=True)
class PostmarkConfig:
    server_token: str
    default_sender: str
    message_stream: str


def send_transactional_email(
    config: PostmarkConfig,
    recipient: str,
    template_id: int,
    template_model: dict,
    cc_recipient: str | None = None,
) -> requests.Response:
    payload = {
        "From": config.default_sender,
        "To": recipient,
        "TemplateId": template_id,
        "TemplateModel": template_model,
        "MessageStream": config.message_stream,
    }
    if cc_recipient:
        payload["Cc"] = cc_recipient
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Postmark-Server-Token": config.server_token,
    }
    response = requests.post(
        POSTMARK_SEND_WITH_TEMPLATE_URL,
        headers=headers,
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    return response
