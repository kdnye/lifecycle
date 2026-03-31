from __future__ import annotations

from dataclasses import dataclass

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


def process_onboarding_request(intake_data: dict) -> dict[str, str | list[str]]:
    """Evaluates intake data and triggers MSP emails through Postmark templates."""
    employee_name = (
        intake_data.get("employee_name")
        or f"{intake_data.get('first_name', '')} {intake_data.get('last_name', '')}".strip()
    )
    role = intake_data.get("role_profile", "")
    tasks_triggered: list[str] = []

    if intake_data.get("needs_m365"):
        success = send_templated_email(
            to_email="support@stellar.tech",
            template_alias="new-user-account",
            template_model={
                "employee_name": employee_name,
                "start_date": intake_data.get("start_date"),
                "manager": intake_data.get("manager"),
                "department": intake_data.get("department"),
            },
        )
        if success:
            tasks_triggered.append("Stellar Support: Account Creation")

    if intake_data.get("needs_hardware"):
        success = send_templated_email(
            to_email="sales@stellar.tech",
            template_alias="hardware-procurement",
            template_model={
                "employee_name": employee_name,
                "role": role,
                "laptop_required": intake_data.get("needs_laptop", False),
                "shipping_location": intake_data.get("location"),
            },
        )
        if success:
            tasks_triggered.append("Stellar Sales: Hardware Order")

    if intake_data.get("needs_phone"):
        success = send_templated_email(
            to_email="support@blackpoint.tech",
            template_alias="telecom-provisioning",
            template_model={
                "employee_name": employee_name,
                "extension_needed": True,
            },
        )
        if success:
            tasks_triggered.append("BlackPoint: Telecom")

    return {"status": "processing", "tasks_generated": tasks_triggered}
