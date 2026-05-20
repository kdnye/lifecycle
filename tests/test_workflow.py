import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import CommunicationOptions, DistributionList, IntakeRequest, RoleMatrix, db
from app.services.workflow import execute_lifecycle_event
from app import create_app


def _build_app():
    os.environ["DATABASE_URL"] = "sqlite:////tmp/lifecycle_test_workflow.db"
    app = create_app()
    app.config.update(TESTING=True, SERVER_NAME="localhost")
    with app.app_context():
        db.drop_all()
        db.create_all()
    return app


def test_onboarding_template_model_contains_permissions_lists(monkeypatch):
    app = _build_app()
    sent_calls = []

    def fake_send_templated_email(**kwargs):
        sent_calls.append(kwargs)
        return True

    with app.app_context():
        role = RoleMatrix(role_profile="office", m365_plan="E3", hardware_default="Laptop", vpn_policy="Standard")
        role.distribution_lists.append(DistributionList(name="Ops", email="ops@example.com", is_active=True))
        db.session.add(role)
        db.session.add(
            CommunicationOptions(
                it_support_email="support@example.com",
                it_sales_email="sales@example.com",
                telecon_sales_email="telecom@example.com",
                internal_notification_list="hr@example.com",
            )
        )
        intake = IntakeRequest(
            first_name="Ada",
            last_name="Lovelace",
            role_profile="office",
            event_type="onboarding",
            manager_email="manager@example.com",
            status="approved",
            needs_equipment=False,
        )
        db.session.add(intake)
        db.session.commit()

        monkeypatch.setattr("app.services.workflow.send_templated_email", fake_send_templated_email)
        result = execute_lifecycle_event(intake.id)

    assert result["status"] == "processed"
    support_call = next(call for call in sent_calls if call.get("template_alias") == "new-user-account")
    model = support_call["template_model"]
    assert "distribution_lists" in model
    assert "file_share_permissions" in model
    assert isinstance(model["distribution_lists"], list)
    assert isinstance(model["file_share_permissions"], list)



def test_hardware_procurement_template_model_requires_request_id(monkeypatch):
    app = _build_app()
    sent_calls = []

    def fake_send_templated_email(**kwargs):
        sent_calls.append(kwargs)
        return True

    with app.app_context():
        role = RoleMatrix(role_profile="office", m365_plan="E3", hardware_default="Laptop", vpn_policy="Standard")
        db.session.add(role)
        db.session.add(
            CommunicationOptions(
                it_support_email="support@example.com",
                it_sales_email="sales@example.com",
                telecon_sales_email="telecom@example.com",
                internal_notification_list="hr@example.com",
            )
        )
        intake = IntakeRequest(
            first_name="Grace",
            last_name="Hopper",
            role_profile="office",
            event_type="onboarding",
            manager_email="manager@example.com",
            status="approved",
            needs_equipment=True,
            equip_status="new",
            equip_type="laptop",
            equip_peripherals="mouse_keyboard",
        )
        db.session.add(intake)
        db.session.commit()

        monkeypatch.setattr("app.services.workflow.send_templated_email", fake_send_templated_email)
        result = execute_lifecycle_event(intake.id)

    assert result["status"] == "processed"
    hardware_call = next(call for call in sent_calls if call.get("template_alias") == "hardware-procurement")
    hardware_model = hardware_call["template_model"]
    assert "request_id" in hardware_model, (
        "hardware-procurement template model must include request_id so Postmark subject mapping "
        "'Hardware Procurement [RequestID: {{request_id}}]' resolves."
    )
