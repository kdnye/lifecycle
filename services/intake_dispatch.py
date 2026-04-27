from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.models import IntakeRequest, db
from services.workflow import initiate_lifecycle_event

TRUTHY_VALUES = {"1", "true", "on", "yes"}


@dataclass(frozen=True)
class IntakeDispatchResult:
    body: dict[str, str]
    status_code: int


def _to_bool(value: object) -> bool:
    return str(value).strip().lower() in TRUTHY_VALUES


def _normalize(payload: dict) -> dict:
    normalized = dict(payload)
    normalized["first_name"] = str(payload.get("first_name", "")).strip()
    normalized["last_name"] = str(payload.get("last_name", "")).strip()
    normalized["manager_email"] = str(payload.get("manager_email", "")).strip()
    normalized["event_type"] = str(payload.get("event_type", "onboarding")).strip() or "onboarding"
    normalized["generated_email"] = str(payload.get("generated_email", "")).strip() or None
    normalized["location"] = str(payload.get("location", "")).strip() or None
    raw_status = str(payload.get("status", "submitted")).strip().lower()
    normalized["status"] = raw_status if raw_status in {"draft", "submitted"} else "submitted"
    return normalized


def process_intake_dispatch(payload: dict) -> IntakeDispatchResult:
    data = _normalize(payload)

    required = ["first_name", "last_name", "start_date", "role_profile", "manager_email"]
    if not all(data.get(field) for field in required):
        return IntakeDispatchResult(
            body={"status": "error", "message": "Missing required fields."},
            status_code=400,
        )

    try:
        datetime.strptime(str(data.get("start_date")), "%Y-%m-%d").date()
    except ValueError:
        return IntakeDispatchResult(
            body={"status": "error", "message": "Invalid date format."},
            status_code=400,
        )

    intake = IntakeRequest(
        first_name=data["first_name"],
        last_name=data["last_name"],
        role_profile=data["role_profile"],
        event_type=data["event_type"],
        manager_email=data["manager_email"],
        generated_email=data.get("generated_email"),
        location=data.get("location"),
        needs_equipment=_to_bool(data.get("needs_equipment")),
        equip_status=data.get("equip_status"),
        equip_type=data.get("equip_type"),
        equip_peripherals=data.get("equip_peripherals"),
        needs_did=_to_bool(data.get("needs_did")),
        area_code=str(data.get("area_code", "")).strip() or None,
        needs_physical_phone=_to_bool(data.get("needs_physical_phone")),
        status=data["status"],
    )
    db.session.add(intake)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return IntakeDispatchResult(
            body={"status": "error", "message": "Unable to create intake request."},
            status_code=500,
        )

    approval_result = initiate_lifecycle_event(intake.id)
    if approval_result.get("status") != "pending_approval":
        return IntakeDispatchResult(
            body={
                "status": "error",
                "message": approval_result.get("message", "Unable to route approval request."),
            },
            status_code=500,
        )

    return IntakeDispatchResult(
        body={
            "status": "pending_approval",
            "message": "Intake submitted and awaiting manager approval before dispatch.",
            "intake_id": intake.id,
        },
        status_code=202,
    )
