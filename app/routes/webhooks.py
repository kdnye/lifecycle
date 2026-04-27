import re

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models import Inventory, db


SERIAL_PATTERN = re.compile(r"(?i)serial\s*number[\s:]*([A-Za-z0-9\-]+)")
REQUEST_ID_PATTERN = re.compile(r"\[RequestID:\s*(\d+)\]")
DEVICE_TYPE_PATTERN = re.compile(r"(?i)device\s*type[\s:]*([A-Za-z][A-Za-z0-9\s\-/]+)")
DEVICE_TYPE_MAP = {
    "laptop": "Laptop",
    "notebook": "Laptop",
    "desktop": "Desktop",
    "workstation": "Desktop",
    "tablet": "Tablet",
    "phone": "Phone",
    "mobile phone": "Phone",
}

webhooks_bp = Blueprint("webhooks", __name__, url_prefix="/api/webhooks")


def _normalize_device_type(raw_device_type: str | None) -> str | None:
    if not raw_device_type:
        return None

    normalized_key = re.sub(r"\s+", " ", raw_device_type.strip().lower())
    mapped = DEVICE_TYPE_MAP.get(normalized_key)
    if mapped:
        return mapped

    return None


@webhooks_bp.post("/postmark-inbound")
def inbound_postmark():
    is_production = bool(current_app.config.get("FSI_PRODUCTION"))
    configured_token = current_app.config.get("POSTMARK_WEBHOOK_TOKEN")
    incoming_token = request.headers.get("X-Postmark-Token", "")

    if is_production and not configured_token:
        current_app.logger.error(
            "webhook_auth_missing_configuration",
            extra={"route": "/api/webhooks/postmark-inbound"},
        )
        return jsonify({"error": "unauthorized webhook"}), 401

    if configured_token and incoming_token != configured_token:
        return jsonify({"error": "unauthorized webhook"}), 401

    payload = request.get_json(silent=True) or {}
    text_body = payload.get("TextBody", "")
    subject = payload.get("Subject", "")

    serial_match = SERIAL_PATTERN.search(text_body)
    request_id_match = REQUEST_ID_PATTERN.search(subject)
    if "[RequestID:" in subject and not request_id_match:
        current_app.logger.info(
            "webhook_parse_miss_request_id",
            extra={"subject": subject},
        )

    if not serial_match:
        current_app.logger.info(
            "webhook_parse_miss_serial",
            extra={"subject": subject},
        )
        return jsonify({"status": "processed"}), 200

    serial_number = serial_match.group(1).strip()
    intake_request_id = int(request_id_match.group(1)) if request_id_match else None
    raw_device_type_match = DEVICE_TYPE_PATTERN.search(text_body)
    device_type = _normalize_device_type(raw_device_type_match.group(1) if raw_device_type_match else None)
    if raw_device_type_match and not device_type:
        current_app.logger.info(
            "webhook_parse_miss_device_type",
            extra={"raw_device_type": raw_device_type_match.group(1)},
        )

    inventory = Inventory(
        serial_number=serial_number,
        device_type=device_type or "Laptop",
        intake_request_id=intake_request_id,
    )

    try:
        db.session.add(inventory)
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        if "unique" in str(exc).lower() and "serial" in str(exc).lower():
            return jsonify({"status": "processed"}), 200
        return jsonify({"error": "invalid inventory payload"}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"error": "database error"}), 500

    return jsonify({"status": "processed"}), 200
