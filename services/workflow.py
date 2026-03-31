from dataclasses import dataclass


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
