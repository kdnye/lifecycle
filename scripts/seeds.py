from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import inspect

from app import create_app
from app.models import ActionMatrix, QuestionMatrix, RoleMatrix, db


@dataclass(frozen=True)
class RoleSeedRow:
    role_profile: str
    m365_plan: str
    hardware_default: str
    vpn_policy: str


@dataclass(frozen=True)
class QuestionSeedRow:
    role_profile: str
    question_key: str
    prompt: str
    is_required: bool


@dataclass(frozen=True)
class ActionSeedRow:
    intake_condition: str
    action_name: str
    target_system: str


ROLE_SEED_ROWS: tuple[RoleSeedRow, ...] = (
    RoleSeedRow("driver", "M365 F1", "BYOD / No default hardware", "No VPN"),
    RoleSeedRow("office", "M365 E3", "Laptop + Dock + Monitors", "Standard VPN"),
    RoleSeedRow("manager", "M365 E3", "Laptop + Dock + Monitors", "Required VPN"),
    RoleSeedRow("warehouse", "M365 Shared/Kiosk", "Shared Workstation", "Internal Network Only"),
    RoleSeedRow("contractor", "M365 Restricted", "BYOD", "Restricted VPN"),
)

QUESTION_SEED_ROWS: tuple[QuestionSeedRow, ...] = (
    QuestionSeedRow(
        "office",
        "needs_non_standard_hardware",
        "Does this office/ops hire need non-standard hardware?",
        False,
    ),
    QuestionSeedRow(
        "office",
        "needs_distribution_lists",
        "Should we assign distribution lists or shared mailbox access?",
        False,
    ),
    QuestionSeedRow(
        "manager",
        "needs_distribution_lists",
        "Should this manager be added to management distribution lists/shared mailboxes?",
        False,
    ),
    QuestionSeedRow(
        "manager",
        "needs_receptionist_access",
        "Does this manager require receptionist/console access?",
        False,
    ),
    QuestionSeedRow(
        "driver",
        "needs_mobile_dispatch",
        "Does the driver require mobile dispatch app provisioning?",
        True,
    ),
    QuestionSeedRow(
        "warehouse",
        "needs_shared_terminal_access",
        "Does the warehouse employee need shared terminal access?",
        True,
    ),
    QuestionSeedRow(
        "contractor",
        "contract_end_date_required",
        "Contractor hard-stop: what is the contract end date?",
        True,
    ),
    QuestionSeedRow(
        "offboarding",
        "is_immediate_termination",
        "Is this offboarding immediate?",
        True,
    ),
    QuestionSeedRow(
        "offboarding",
        "mailbox_forwarding_target",
        "Should mailbox forwarding be enabled, and to which address?",
        False,
    ),
)

ACTION_SEED_ROWS: tuple[ActionSeedRow, ...] = (
    ActionSeedRow("onboarding:any:m365", "create-m365-account", "Stellar Support"),
    ActionSeedRow("onboarding:office_or_manager:hardware", "create-hardware-ticket", "Stellar Sales"),
    ActionSeedRow("onboarding:phone_or_extension_required", "create-telecom-ticket", "BlackPoint"),
    ActionSeedRow("onboarding:driver:internal-assets", "create-fleet-provisioning-ticket", "FSI Ops"),
    ActionSeedRow("offboarding:immediate", "priority-revocation", "Stellar Support"),
    ActionSeedRow("offboarding:scheduled", "standard-revocation", "Stellar Support"),
    ActionSeedRow("offboarding:driver", "asset-recovery-routing", "FSI Ops"),
)


def _ensure_required_tables_exist() -> None:
    inspector = inspect(db.engine)
    required_tables = {RoleMatrix.__tablename__, QuestionMatrix.__tablename__, ActionMatrix.__tablename__}
    existing_tables = set(inspector.get_table_names())
    missing_tables = sorted(required_tables - existing_tables)
    if missing_tables:
        missing_csv = ", ".join(missing_tables)
        raise RuntimeError(
            f"Cannot seed baseline policy rows; missing tables: {missing_csv}. "
            "Run `flask db upgrade` (or `alembic upgrade head`) first."
        )


def _upsert_role_rows() -> int:
    changed = 0
    for row in ROLE_SEED_ROWS:
        existing_rows = RoleMatrix.query.filter_by(role_profile=row.role_profile).order_by(RoleMatrix.id.asc()).all()
        if not existing_rows:
            db.session.add(
                RoleMatrix(
                    role_profile=row.role_profile,
                    m365_plan=row.m365_plan,
                    hardware_default=row.hardware_default,
                    vpn_policy=row.vpn_policy,
                )
            )
            changed += 1
            continue

        canonical = existing_rows[0]
        if (
            canonical.m365_plan != row.m365_plan
            or canonical.hardware_default != row.hardware_default
            or canonical.vpn_policy != row.vpn_policy
        ):
            canonical.m365_plan = row.m365_plan
            canonical.hardware_default = row.hardware_default
            canonical.vpn_policy = row.vpn_policy
            changed += 1

        for duplicate in existing_rows[1:]:
            db.session.delete(duplicate)
            changed += 1

    return changed


def _upsert_question_rows() -> int:
    changed = 0
    for row in QUESTION_SEED_ROWS:
        existing_rows = (
            QuestionMatrix.query.filter_by(role_profile=row.role_profile, question_key=row.question_key)
            .order_by(QuestionMatrix.id.asc())
            .all()
        )
        if not existing_rows:
            db.session.add(
                QuestionMatrix(
                    role_profile=row.role_profile,
                    question_key=row.question_key,
                    prompt=row.prompt,
                    is_required=row.is_required,
                )
            )
            changed += 1
            continue

        canonical = existing_rows[0]
        if canonical.prompt != row.prompt or canonical.is_required != row.is_required:
            canonical.prompt = row.prompt
            canonical.is_required = row.is_required
            changed += 1

        for duplicate in existing_rows[1:]:
            db.session.delete(duplicate)
            changed += 1

    return changed


def _upsert_action_rows() -> int:
    changed = 0
    for row in ACTION_SEED_ROWS:
        existing_rows = (
            ActionMatrix.query.filter_by(intake_condition=row.intake_condition, action_name=row.action_name)
            .order_by(ActionMatrix.id.asc())
            .all()
        )
        if not existing_rows:
            db.session.add(
                ActionMatrix(
                    intake_condition=row.intake_condition,
                    action_name=row.action_name,
                    target_system=row.target_system,
                )
            )
            changed += 1
            continue

        canonical = existing_rows[0]
        if canonical.target_system != row.target_system:
            canonical.target_system = row.target_system
            changed += 1

        for duplicate in existing_rows[1:]:
            db.session.delete(duplicate)
            changed += 1

    return changed


def seed_baseline_policy_rows() -> int:
    _ensure_required_tables_exist()
    total_changes = 0
    total_changes += _upsert_role_rows()
    total_changes += _upsert_question_rows()
    total_changes += _upsert_action_rows()
    db.session.commit()
    return total_changes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Seed baseline RoleMatrix, QuestionMatrix, and ActionMatrix rows (idempotent)."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero if no row changes were applied.",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        changes = seed_baseline_policy_rows()

    print(f"Baseline seed complete. Rows inserted/updated/deduplicated: {changes}")
    if args.strict and changes == 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
