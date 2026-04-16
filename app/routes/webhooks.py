import re

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models import Inventory, db


webhooks_bp = Blueprint("webhooks", __name__)


@webhooks_bp.post("/inbound-postmark")
def inbound_postmark():
    configured_token = current_app.config.get("POSTMARK_WEBHOOK_TOKEN")
    if configured_token:
        incoming_token = request.headers.get("X-Postmark-Token", "")
        if incoming_token != configured_token:
            return jsonify({"error": "unauthorized webhook"}), 401

    payload = request.get_json(silent=True) or {}
    text_body = payload.get("TextBody", "")
    subject = payload.get("Subject", "")

    serial_match = re.search(r"(?i)serial\s*number[\s:]*([A-Za-z0-9\-]+)", text_body)
    request_id_match = re.search(r"\[RequestID:\s*(\d+)\]", subject)

    if not serial_match:
        return jsonify({"status": "processed"}), 200

    serial_number = serial_match.group(1).strip()
    intake_request_id = int(request_id_match.group(1)) if request_id_match else None

    inventory = Inventory(
        serial_number=serial_number,
        intake_request_id=intake_request_id,
    )

    try:
        db.session.add(inventory)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "invalid inventory payload"}), 400
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({"error": "database error"}), 500

    return jsonify({"status": "processed"}), 200
