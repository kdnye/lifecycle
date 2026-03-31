from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from datetime import date
import os

from flask import current_app, url_for

from app.models import IntakeRequest, User, db
from services.email import send_templated_email


@dataclass(frozen=True)
class IntakeContext:
    employee_name: str
    role_profile: str
    event_type: str
    manager_name: str | None = None


def build_action_plan(context: IntakeContext) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []

    if context.event_type == "onboarding":
        actions.append({"action": "Create M365 account", "vendor": "Stellar Support"})
        if context.role_profile in {"office", "manager"}:
            actions.append({"action": "Provision laptop and dock", "vendor": "Stellar Sales"})
    elif context.event_type == "offboarding":
        actions.append({"action": "Revoke AD and M365 sessions", "vendor": "Stellar Support"})

    return actions


def generate_secure_temp_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _build_generated_email(first_name: str, last_name: str) -> str:
    sanitized_first = first_name.strip().lower().replace(" ", "")
    sanitized_last = last_name.strip().lower().replace(" ", "")
    return f"{sanitized_first}.{sanitized_last}@freightservices.net"


def _build_cc_targets(manager_email: str | None) -> tuple[str, str]:
    hr_cc_raw = current_app.config.get("HR_CC_EMAILS", "")
    hr_cc_list = [email.strip() for email in hr_cc_raw.split(",") if email.strip()]
    cc_targets = list(hr_cc_list)

    if manager_email and manager_email not in cc_targets:
        cc_targets.append(manager_email)

    primary_to_email = hr_cc_list[0] if hr_cc_list else (manager_email or "")
    return ", ".join(cc_targets), primary_to_email


def initiate_lifecycle_event(intake_id: int) -> dict[str, str | int]:
    """Phase 1: Hold execution and request manager approval."""
    intake_request = db.session.get(IntakeRequest, intake_id)
    if not intake_request:
        return {"status": "error", "message": "Request not found.", "intake_id": intake_id}

    manager_email = (intake_request.manager_email or "").strip() or None
    _, primary_hr_email = _build_cc_targets(manager_email)
    approver_email = manager_email or primary_hr_email

    if not approver_email:
        return {
            "status": "error",
            "message": "Unable to route approval email. Configure HR_CC_EMAILS or manager email.",
            "intake_id": intake_id,
        }

    approval_url = url_for("intake.approve_request", token=intake_request.approval_token, _external=True)
    rejection_url = url_for("intake.reject_request", token=intake_request.approval_token, _external=True)

    sent = send_templated_email(
        to_email=approver_email,
        template_alias="manager-approval-required",
        template_model={
            "employee_name": f"{intake_request.first_name} {intake_request.last_name}",
            "event_type": intake_request.event_type.upper(),
            "role": intake_request.role_profile,
            "approve_url": approval_url,
            "reject_url": rejection_url,
        },
    )
    if not sent:
        return {
            "status": "error",
            "message": "Failed to send manager approval email via Postmark.",
            "intake_id": intake_id,
        }

    intake_request.status = "pending_approval"
    db.session.commit()
    return {
        "status": "pending_approval",
        "message": f"Approval routed to {approver_email}",
        "intake_id": intake_id,
    }


def _execute_onboarding(intake_request: IntakeRequest) -> list[str]:
    generated_email = _build_generated_email(intake_request.first_name, intake_request.last_name)
    manager_email = (intake_request.manager_email or "").strip() or None
    ops_email = os.getenv("FSI_OPS_EMAIL", "ops@freightservices.net")
    cc_email, primary_hr_email = _build_cc_targets(manager_email)
    tasks_triggered: list[str] = []

    existing_user = User.query.filter_by(email=generated_email).first()
    if not existing_user:
        new_user = User(
            email=generated_email,
            name=f"{intake_request.first_name} {intake_request.last_name}",
            first_name=intake_request.first_name,
            last_name=intake_request.last_name,
            role="EMPLOYEE",
            employee_approved=True,
            is_active=True,
        )
        new_user.set_password(generate_secure_temp_password())
        db.session.add(new_user)
        db.session.flush()
        tasks_triggered.append("FSI Shared Identity: User Provisioned")

    manager_notification_to = manager_email or primary_hr_email
    if manager_notification_to:
        manager_notified = send_templated_email(
            to_email=manager_notification_to,
            cc_email=cc_email or None,
            template_alias="manager-onboarding-notification",
            template_model={
                "employee_name": f"{intake_request.first_name} {intake_request.last_name}",
                "role": intake_request.role_profile,
                "requested_email": generated_email,
            },
        )
        if manager_notified:
            tasks_triggered.append(f"Internal Welcome Notified: {manager_notification_to}")

    if intake_request.role_profile == "driver":
        assets_needed: list[str] = []
        if intake_request.driver_needs_laptop:
            assets_needed.append("Laptop")
        if intake_request.driver_needs_printer:
            assets_needed.append("Mobile Printer")
        if intake_request.driver_needs_fuel_card:
            assets_needed.append("Fuel Card")
        if intake_request.driver_needs_vehicle:
            assets_needed.append("Box Truck Assignment")

        if assets_needed:
            ops_notified = send_templated_email(
                to_email=ops_email,
                cc_email=cc_email or None,
                template_alias="internal-fleet-provisioning",
                template_model={
                    "employee_name": f"{intake_request.first_name} {intake_request.last_name}",
                    "event_type": "Onboarding",
                    "assets_list": ", ".join(assets_needed),
                    "manager": manager_email or "Unassigned",
                },
            )
            if ops_notified:
                tasks_triggered.append(f"FSI Ops: Provision Internal Assets ({len(assets_needed)} items)")

    email_sent = send_templated_email(
        to_email="support@stellar.tech",
        cc_email=cc_email or None,
        template_alias="new-user-account",
        template_model={
            "employee_name": f"{intake_request.first_name} {intake_request.last_name}",
            "requested_email": generated_email,
            "role": intake_request.role_profile,
        },
    )
    if not email_sent:
        raise RuntimeError("Failed to notify Stellar Support via Postmark.")

    tasks_triggered.append("Stellar Support: Account Creation")
    return tasks_triggered


def _format_termination_date(termination_date: date | None, is_immediate: bool) -> str:
    if is_immediate:
        return "Immediate"
    if termination_date:
        return termination_date.isoformat()
    return "Not Provided"


def _execute_offboarding(intake_request: IntakeRequest) -> list[str]:
    generated_email = _build_generated_email(intake_request.first_name, intake_request.last_name)
    manager_email = (intake_request.manager_email or "").strip() or None
    cc_email, _ = _build_cc_targets(manager_email)
    tasks_triggered: list[str] = []

    user = User.query.filter_by(email=generated_email).first()
    if user and user.is_active:
        user.is_active = False
        db.session.flush()
        tasks_triggered.append("FSI Shared Identity Deactivated")

    template_alias = "offboarding-immediate" if intake_request.is_immediate else "offboarding-standard"
    stellar_sent = send_templated_email(
        to_email="support@stellar.tech",
        cc_email=cc_email or None,
        template_alias=template_alias,
        template_model={
            "employee_name": f"{intake_request.first_name} {intake_request.last_name}",
            "current_email": generated_email,
            "termination_date": _format_termination_date(
                intake_request.termination_date,
                intake_request.is_immediate,
            ),
            "forwarding_target": intake_request.forwarding_email or "None",
        },
    )
    if not stellar_sent:
        raise RuntimeError("Failed to notify Stellar Support for offboarding.")
    tasks_triggered.append(f"Stellar Ticket: {template_alias}")

    if intake_request.role_profile == "driver":
        ops_sent = send_templated_email(
            to_email="ops@freightservices.net",
            cc_email=cc_email or None,
            template_alias="internal-fleet-provisioning",
            template_model={
                "employee_name": f"{intake_request.first_name} {intake_request.last_name}",
                "event_type": "OFFBOARDING - RECOVERY",
                "assets_list": "Recover Laptop, Mobile Printer, Fuel Card, Keys",
            },
        )
        if ops_sent:
            tasks_triggered.append("Ops Ticket: Asset Recovery")

    return tasks_triggered


def execute_lifecycle_event(intake_id: int) -> dict[str, str | int | list[str]]:
    """Phase 2: Execute workflow after manager approval."""
    intake_request = db.session.get(IntakeRequest, intake_id)
    if not intake_request:
        return {"status": "error", "message": "Request not found.", "intake_id": intake_id}

    if intake_request.status != "approved":
        return {
            "status": "error",
            "message": "Event not approved for execution.",
            "intake_id": intake_id,
        }

    try:
        if intake_request.event_type == "onboarding":
            tasks_triggered = _execute_onboarding(intake_request)
        elif intake_request.event_type == "offboarding":
            tasks_triggered = _execute_offboarding(intake_request)
        else:
            return {
                "status": "error",
                "message": f"Unsupported event_type '{intake_request.event_type}'.",
                "intake_id": intake_id,
            }

        intake_request.status = "processed"
        db.session.commit()
        return {"status": "processed", "intake_id": intake_id, "tasks_generated": tasks_triggered}
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Lifecycle execution failed for intake %s", intake_id)
        return {"status": "error", "message": str(exc), "intake_id": intake_id}


def process_onboarding_request(intake_id: int) -> dict[str, str | list[str] | int]:
    """Backward compatible wrapper for existing callers."""
    intake_request = db.session.get(IntakeRequest, intake_id)
    if not intake_request:
        return {"status": "error", "message": "Intake request not found.", "intake_id": intake_id}

    if intake_request.event_type != "onboarding":
        return {
            "status": "error",
            "message": "Only onboarding intake requests are eligible for processing.",
            "intake_id": intake_id,
        }

    intake_request.status = "approved"
    db.session.commit()
    return execute_lifecycle_event(intake_id)
