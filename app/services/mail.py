from __future__ import annotations

from app.services.email import send_templated_email


def send_transactional_mail_async(
    recipient: str,
    subject: str,
    template_name: str,
    template_model: dict,
    cc: str | None = None,
    feature: str | None = None,
) -> bool:
    """Postmark-backed wrapper for transactional template dispatches."""
    model = dict(template_model)
    model.setdefault("email_subject", subject)
    if feature:
        model.setdefault("feature", feature)

    return send_templated_email(
        to_email=recipient,
        cc_email=cc,
        template_alias=template_name,
        template_model=model,
    )
