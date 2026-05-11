import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import DistributionList, FileSharePermission, RoleMatrix, db
from app.services.permission_service import get_role_permissions
from app import create_app


def _build_app():
    os.environ["DATABASE_URL"] = "sqlite:////tmp/lifecycle_test_permissions.db"
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.drop_all()
        db.create_all()
    return app


def test_get_role_permissions_returns_active_assignments_only():
    app = _build_app()
    with app.app_context():
        role = RoleMatrix(
            role_profile="office",
            m365_plan="M365 E3",
            hardware_default="Laptop",
            vpn_policy="Standard VPN",
        )
        active_dl = DistributionList(name="Operations", email="ops@example.com", is_active=True)
        inactive_dl = DistributionList(name="Old Team", email="old@example.com", is_active=False)
        active_share = FileSharePermission(
            name="Ops Drive",
            resource_path="\\\\fileserver\\ops",
            access_level="read",
            is_active=True,
        )
        inactive_share = FileSharePermission(
            name="Legacy Drive",
            resource_path="\\\\fileserver\\legacy",
            access_level="write",
            is_active=False,
        )

        role.distribution_lists.extend([active_dl, inactive_dl])
        role.file_share_permissions.extend([active_share, inactive_share])
        db.session.add(role)
        db.session.commit()

        permissions = get_role_permissions("office")
        assert permissions["distribution_lists"] == ["Operations <ops@example.com>"]
        assert permissions["file_share_permissions"] == ["Ops Drive (\\\\fileserver\\ops) - read"]
