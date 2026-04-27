from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from datetime import date

from flask import current_app, url_for

from app.models import IntakeRequest, User, db
from services.communication_options import get_communication_options
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
    options = get_communication_options()
    internal_cc_raw = options.internal_notification_list
    internal_cc_list = [email.strip() for email in internal_cc_raw.split(",") if email.strip()]

    hr_cc_raw = current_app.config.get("HR_CC_EMAILS", "")
    hr_cc_list = [email.strip() for email in hr_cc_raw.split(",") if email.strip()]

    cc_targets: list[str] = []
    for email in [*internal_cc_list, *hr_cc_list]:
        if email and email not in cc_targets:
            cc_targets.append(email)

    if manager_email and manager_email not in cc_targets:
        cc_targets.append(manager_email)

    primary_to_email = cc_targets[0] if cc_targets else (manager_email or "")
    return ", ".join(cc_targets), primary_to_email


def _onboarding_message_stream() -> str:
    return current_app.config.get(
        "POSTMARK_ONBOARDING_MESSAGE_STREAM",
        current_app.config.get("MAIL_MESSAGE_STREAM", "outbound"),
    )


def initiate_lifecycle_event(intake_id: int) -> dict[str, str | int]:
    """Phase 1: Hold execution and request manager approval."""
    intake_request = db.session.get(IntakeRequest, intake_id)
    if not intake_request:
        return {
            "status": "error",
            "message": "Request not found.",
            "remediation": f"Confirm intake_id={intake_id} exists before initiating approval.",
            "intake_id": intake_id,
        }

    manager_email = (intake_request.manager_email or "").strip() or None
    _, primary_hr_email = _build_cc_targets(manager_email)
    approver_email = manager_email or primary_hr_email

    if not approver_email:
        return {
            "status": "error",
            "message": "Unable to route approval email. Configure HR_CC_EMAILS or manager email.",
            "remediation": "Set a valid manager_email on the intake request or configure HR_CC_EMAILS, then retry.",
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
        message_stream=_onboarding_message_stream() if intake_request.event_type == "onboarding" else None,
    )
    if not sent:
        return {
            "status": "error",
            "message": "Failed to send manager approval email via Postmark.",
            "remediation": "Verify POSTMARK_SERVER_TOKEN, DEFAULT_SENDER_EMAIL, and template alias 'manager-approval-required', then retry.",
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
    ops_email = current_app.config.get("FSI_OPS_EMAIL")
    communication_options = get_communication_options()
    stellar_support_email = communication_options.it_support_email
    stellar_sales_email = communication_options.it_sales_email
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
            message_stream=_onboarding_message_stream(),
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
                message_stream=_onboarding_message_stream(),
            )
            if ops_notified:
                tasks_triggered.append(f"FSI Ops: Provision Internal Assets ({len(assets_needed)} items)")

    equipment_status = (intake_request.equip_status or "").strip().lower()
    equipment_type = (intake_request.equip_type or "").strip().lower()
    peripheral_raw = (intake_request.equip_peripherals or "").strip()
    peripheral_map = {
        "fsi_stock": "Use FSI stock",
        "mouse_keyboard": "Mouse + Keyboard",
        "wireless_laptop_peripherals": "Wireless laptop peripherals",
        "personal": "Employee personal peripherals",
    }
    peripheral_labels = ", ".join(
        peripheral_map.get(item.strip(), item.strip())
        for item in peripheral_raw.split(",")
        if item.strip()
    ) or "None provided"

    email_sent = send_templated_email(
        to_email=stellar_support_email,
        cc_email=cc_email or None,
        template_alias="new-user-account",
        template_model={
            "employee_name": f"{intake_request.first_name} {intake_request.last_name}",
            "requested_email": generated_email,
            "role": intake_request.role_profile,
            "needs_equipment": intake_request.needs_equipment,
            "equip_status": equipment_status or "not_provided",
            "equip_type": equipment_type or "not_provided",
            "equip_peripherals": peripheral_labels,
            "new_equipment_sales_notice": (
                "NEW Equipment Needs to Be Ordered. Please pass the below to sales:"
                if intake_request.needs_equipment and equipment_status == "new"
                else ""
            ),
            "stellar_ordering_scope": "Stellar only orders computers/laptops/docks. Non-compute peripherals are ordered internally.",
        },
        message_stream=_onboarding_message_stream(),
    )
    if not email_sent:
        raise RuntimeError(
            "Failed to notify Stellar Support via Postmark. Remediation: verify Postmark credentials, "
            "recipient configuration, and template alias 'new-user-account'."
        )

    tasks_triggered.append("Stellar Support: Account Creation")

    if intake_request.role_profile in {"office", "manager"}:
        hardware_template_model = {
            "employee_name": f"{intake_request.first_name} {intake_request.last_name}",
            "requested_email": generated_email,
            "role": intake_request.role_profile,
            "equip_status": equipment_status or "not_provided",
            "equip_type": equipment_type or "not_provided",
            "equip_peripherals": peripheral_labels,
            # Subject/body rendering stays in Postmark template configuration.
            # request_id is provided so Postmark can render:
            # "Hardware Procurement [RequestID: {{request_id}}]"
            "request_id": intake_request.id,
        }
        hardware_procurement_sent = send_templated_email(
            to_email=stellar_sales_email,
            cc_email=cc_email or None,
            template_alias="hardware-procurement",
            template_model=hardware_template_model,
            message_stream=_onboarding_message_stream(),
        )
        if not hardware_procurement_sent:
            raise RuntimeError(
                "Failed to notify Stellar Sales for hardware procurement. Remediation: verify template alias "
                "'hardware-procurement' and Stellar Sales destination email configuration."
            )
        tasks_triggered.append("Stellar Sales: Hardware Procurement")

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
    communication_options = get_communication_options()
    stellar_support_email = communication_options.it_support_email
    ops_email = communication_options.telecon_sales_email
    cc_email, _ = _build_cc_targets(manager_email)
    tasks_triggered: list[str] = []

    user = User.query.filter_by(email=generated_email).first()
    if user and user.is_active:
        user.is_active = False
        db.session.flush()
        tasks_triggered.append("FSI Shared Identity Deactivated")

    template_alias = "offboarding-immediate" if intake_request.is_immediate else "offboarding-standard"
    stellar_sent = send_templated_email(
        to_email=stellar_support_email,
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
        raise RuntimeError(
            "Failed to notify Stellar Support for offboarding. Remediation: verify template aliases "
            "'offboarding-immediate'/'offboarding-standard' and Postmark configuration."
        )
    tasks_triggered.append(f"Stellar Ticket: {template_alias}")

    if intake_request.role_profile == "driver":
        ops_sent = send_templated_email(
            to_email=ops_email,
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
        return {
            "status": "error",
            "message": "Request not found.",
            "remediation": f"Confirm intake_id={intake_id} exists before executing lifecycle actions.",
            "intake_id": intake_id,
        }

    if intake_request.status != "approved":
        return {
            "status": "error",
            "message": "Event not approved for execution.",
            "remediation": "Approve the request from /intake/approve/<token> before executing lifecycle actions.",
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
                "remediation": "Use event_type 'onboarding' or 'offboarding' for lifecycle execution.",
                "intake_id": intake_id,
            }

        intake_request.status = "processed"
        db.session.commit()
        return {"status": "processed", "intake_id": intake_id, "tasks_generated": tasks_triggered}
    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Lifecycle execution failed for intake %s", intake_id)
        return {
            "status": "error",
            "message": str(exc),
            "remediation": "Check application logs for stack trace details, resolve configuration/data issues, then retry execution.",
            "intake_id": intake_id,
        }
