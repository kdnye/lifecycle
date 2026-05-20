import re

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models import AssetStatus, IntakeRequest, Inventory, db


SERIAL_PATTERN = re.compile(r"(?i)serial\s*number[\s:]*([A-Za-z0-9\-]+)")
REQUEST_ID_PATTERN = re.compile(r"\[RequestID:\s*(\d+)\]")

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/api/webhooks")

CANONICAL_POSTMARK_INBOUND_PATH = "/api/webhooks/postmark-inbound"

MANUAL_REVIEW_STATUS = "Needs Manual Review"
NON_REGRESSIVE_INTAKE_STATUSES = {"approved", "processed", "rejected"}


def _maybe_mark_manual_review(intake_request: IntakeRequest | None) -> bool:
    """Set a controlled status for parse failures without regressing terminal states."""
    if not intake_request:
        return False

    current_status = (intake_request.status or "").strip().lower()
    if current_status in NON_REGRESSIVE_INTAKE_STATUSES:
        return False
    if intake_request.status == MANUAL_REVIEW_STATUS:
        return False

    intake_request.status = MANUAL_REVIEW_STATUS
    return True


@webhooks_bp.post("/postmark-inbound")
@webhooks_bp.post("/inbound-postmark")
def inbound_postmark():
    is_production = bool(current_app.config.get("FSI_PRODUCTION"))
    configured_token = current_app.config.get("POSTMARK_WEBHOOK_TOKEN")
    incoming_token = request.headers.get("X-Postmark-Token", "")

    if is_production and not configured_token:
        current_app.logger.error(
            "webhook_auth_missing_configuration",
            extra={"route": CANONICAL_POSTMARK_INBOUND_PATH},
        )
        return (
            jsonify(
                {
                    "error": "unauthorized webhook",
                    "remediation": "Configure POSTMARK_WEBHOOK_TOKEN for production and resend the webhook.",
                }
            ),
            401,
        )

    if configured_token and incoming_token != configured_token:
        return (
            jsonify(
                {
                    "error": "unauthorized webhook",
                    "remediation": "Send header X-Postmark-Token matching POSTMARK_WEBHOOK_TOKEN.",
                }
            ),
            401,
        )

    payload = request.get_json(silent=True) or {}
    text_body = payload.get("TextBody", "")
    subject = payload.get("Subject", "")

    serial_match = SERIAL_PATTERN.search(text_body)
    request_id_match = REQUEST_ID_PATTERN.search(subject)

    intake_request_id = int(request_id_match.group(1)) if request_id_match else None
    intake_request = db.session.get(IntakeRequest, intake_request_id) if intake_request_id else None

    if "[RequestID:" in subject and not request_id_match:
        current_app.logger.info(
            "webhook_parse_miss_request_id",
            extra={"subject": subject, "request_id": None, "failure_reason": "invalid_request_id"},
        )

    if request_id_match and not intake_request:
        current_app.logger.info(
            "webhook_intake_lookup_miss",
            extra={"subject": subject, "request_id": intake_request_id, "failure_reason": "invalid_request_id"},
        )

    if not serial_match:
        status_updated = _maybe_mark_manual_review(intake_request)
        try:
            if status_updated:
                db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            return (
                jsonify(
                    {
                        "error": "database error",
                        "remediation": "Verify database availability and run pending migrations, then retry webhook delivery.",
                    }
                ),
                500,
            )

        current_app.logger.info(
            "webhook_parse_miss_serial",
            extra={
                "subject": subject,
                "request_id": intake_request_id,
                "failure_reason": "serial_parse_miss",
                "intake_status_updated": status_updated,
            },
        )
        return jsonify({"status": "processed"}), 200

    serial_number = serial_match.group(1).strip()

    inventory = Inventory(
        serial_number=serial_number,
        status=AssetStatus.AVAILABLE,
        intake_request_id=intake_request_id,
    )

    try:
        db.session.add(inventory)
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        if "unique" in str(exc).lower() and "serial" in str(exc).lower():
            return jsonify({"status": "processed"}), 200
        return (
            jsonify(
                {
                    "error": "invalid inventory payload",
                    "remediation": "Validate inbound serial/device fields and RequestID mapping, then retry with corrected payload.",
                }
            ),
            400,
        )
    except SQLAlchemyError:
        db.session.rollback()
        return (
            jsonify(
                {
                    "error": "database error",
                    "remediation": "Verify database availability and run pending migrations, then retry webhook delivery.",
                }
            ),
            500,
        )

    return jsonify({"status": "processed"}), 200
