from __future__ import annotations

import re

from app.models import INTAKE_REQUEST_TABLE, INVENTORY_TABLE, IntakeRequest, Inventory, db

MANUAL_REVIEW_STATUS = "Needs Manual Review"
PROVISIONED_STATUS = "Hardware Provisioned"
_SERIAL_CLEAN_RE = re.compile(r"[^A-Za-z0-9-]+")


class HardwareReviewValidationError(ValueError):
    """Validation failure with remediation guidance suitable for UI flash messages."""


def list_manual_review_requests() -> list[IntakeRequest]:
    return (
        db.session.query(IntakeRequest)
        .filter(IntakeRequest.status == MANUAL_REVIEW_STATUS)
        .order_by(IntakeRequest.id.asc())
        .all()
    )


def normalize_serial(raw_serial: str | None) -> str:
    serial = (raw_serial or "").strip().upper()
    serial = _SERIAL_CLEAN_RE.sub("", serial)
    return serial


def resolve_hardware_review(intake_request_id: int | None, serial_number: str | None) -> tuple[IntakeRequest, Inventory]:
    if not intake_request_id:
        raise HardwareReviewValidationError(
            "Request ID is required. Remediation: select a pending intake request and try again."
        )

    intake = db.session.get(IntakeRequest, intake_request_id)
    if intake is None:
        raise HardwareReviewValidationError(
            "Selected request was not found. Remediation: refresh Hardware Review and choose a valid request."
        )
    if intake.status != MANUAL_REVIEW_STATUS:
        raise HardwareReviewValidationError(
            "Request is not in Needs Manual Review. Remediation: only unresolved requests can be provisioned here."
        )

    normalized_serial = normalize_serial(serial_number)
    if not normalized_serial:
        raise HardwareReviewValidationError(
            "Serial number is required. Remediation: enter the asset serial and submit again."
        )

    duplicate = (
        db.session.query(Inventory)
        .filter(Inventory.serial_number == normalized_serial, Inventory.intake_request_id != intake.id)
        .first()
    )
    if duplicate is not None:
        raise HardwareReviewValidationError(
            "Serial number already exists on another inventory record. Remediation: confirm the tag and use a unique serial."
        )

    inventory = (
        db.session.query(Inventory)
        .filter(Inventory.intake_request_id == intake.id)
        .one_or_none()
    )
    if inventory is None:
        inventory = Inventory(intake_request_id=intake.id, serial_number=normalized_serial)
        db.session.add(inventory)
    else:
        inventory.serial_number = normalized_serial

    intake.status = PROVISIONED_STATUS
    db.session.commit()
    return intake, inventory
