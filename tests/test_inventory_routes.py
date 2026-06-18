import pytest
from app.models import AssetStatus, Inventory, db


def test_list_assets_requires_login(client):
    response = client.get("/inventory/")
    assert response.status_code == 302


def test_list_assets_authenticated(app, logged_in_client):
    client, user = logged_in_client
    asset = Inventory(asset_number="TAG-001", status=AssetStatus.AVAILABLE)
    db.session.add(asset)
    db.session.commit()

    response = client.get("/inventory/")
    assert response.status_code == 200
    assert b"TAG-001" in response.data


def test_asset_detail(app, logged_in_client):
    client, user = logged_in_client
    asset = Inventory(asset_number="TAG-002", make="Dell", status=AssetStatus.AVAILABLE)
    db.session.add(asset)
    db.session.commit()
    asset_id = asset.id

    response = client.get(f"/inventory/{asset_id}")
    assert response.status_code == 200
    assert b"Dell" in response.data


def test_create_asset(app, logged_in_client):
    client, user = logged_in_client

    response = client.post(
        "/inventory/new",
        data={
            "asset_number": "NEW-TAG",
            "it_asset_tag": "IT-0001",
            "serial_number": "SN-NEW",
            "status": "Available",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    asset = Inventory.query.filter_by(it_asset_tag="IT-0001").first()
    assert asset is not None
    assert asset.status == AssetStatus.AVAILABLE
    assert asset.asset_number == "NEW-TAG"


def test_create_quantity_asset(app, logged_in_client):
    client, user = logged_in_client

    response = client.post(
        "/inventory/new",
        data={
            "make": "Anker",
            "model_name": "USB-C Cable",
            "tracking_mode": "Quantity",
            "quantity": "50",
            "status": "Available",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    asset = Inventory.query.filter_by(model_name="USB-C Cable").first()
    assert asset is not None
    assert asset.tracking_mode.value == "Quantity"
    assert asset.quantity == 50


def test_scan_lookup_not_found(app, logged_in_client):
    client, user = logged_in_client

    response = client.post(
        "/inventory/scan",
        json={"tag": "NOTFOUND-999"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["found"] is False
    assert data["tag"] == "NOTFOUND-999"


def test_scan_lookup_found(app, logged_in_client):
    client, user = logged_in_client
    asset = Inventory(asset_number="SCAN-TAG", status=AssetStatus.AVAILABLE)
    db.session.add(asset)
    db.session.commit()

    response = client.post(
        "/inventory/scan",
        json={"tag": "SCAN-TAG"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["found"] is True
    assert data["id"] == asset.id
    assert "detail_url" in data


def test_audit_mode_renders(app, logged_in_client):
    client, user = logged_in_client

    response = client.get("/inventory/audit")

    assert response.status_code == 200
    assert b"Inventory Mode" in response.data
    assert b"Link to Current IT Asset Tag" in response.data


def test_link_fsi_to_it_tag_updates_existing_asset(app, logged_in_client):
    client, user = logged_in_client
    asset = Inventory(it_asset_tag="IT-7788", status=AssetStatus.AVAILABLE)
    db.session.add(asset)
    db.session.commit()
    asset_id = asset.id

    response = client.post(
        "/inventory/audit/link",
        data={"fsi_number": "FSI7788", "it_asset_tag": "IT-7788"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/inventory/{asset_id}/edit")
    updated = db.session.get(Inventory, asset_id)
    assert updated.asset_number == "FSI7788"


def test_link_fsi_to_it_tag_redirects_when_target_missing(app, logged_in_client):
    client, user = logged_in_client

    response = client.post(
        "/inventory/audit/link",
        data={"fsi_number": "FSI9999", "it_asset_tag": "UNKNOWN"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/inventory/audit")


def test_link_fsi_to_it_tag_requires_both_inputs(app, logged_in_client):
    client, user = logged_in_client

    response = client.post(
        "/inventory/audit/link",
        data={"fsi_number": "", "it_asset_tag": ""},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/inventory/audit")


def test_link_fsi_to_it_tag_rejects_existing_fsi_number(app, logged_in_client):
    client, user = logged_in_client
    existing_fsi_asset = Inventory(asset_number="FSI7788", status=AssetStatus.AVAILABLE)
    target_asset = Inventory(it_asset_tag="IT-7788", status=AssetStatus.AVAILABLE)
    db.session.add_all([existing_fsi_asset, target_asset])
    db.session.commit()
    target_asset_id = target_asset.id

    response = client.post(
        "/inventory/audit/link",
        data={"fsi_number": "FSI7788", "it_asset_tag": "IT-7788"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/inventory/audit")
    updated_target = db.session.get(Inventory, target_asset_id)
    assert updated_target.asset_number is None


def test_archive_asset(app, logged_in_client):
    client, user = logged_in_client
    asset = Inventory(asset_number="ARCH-TAG", status=AssetStatus.AVAILABLE)
    db.session.add(asset)
    db.session.commit()
    asset_id = asset.id

    response = client.post(
        f"/inventory/{asset_id}/archive",
        follow_redirects=True,
    )
    assert response.status_code == 200

    updated = db.session.get(Inventory, asset_id)
    assert updated.status == AssetStatus.RETIRED


def test_export_assets_csv_requires_login(client):
    response = client.get("/inventory/export.csv")
    assert response.status_code == 302


def test_export_assets_csv_returns_rows(app, logged_in_client):
    client, user = logged_in_client
    db.session.add_all(
        [
            Inventory(asset_number="EXP-001", status=AssetStatus.AVAILABLE),
            Inventory(asset_number="EXP-002", status=AssetStatus.ASSIGNED),
        ]
    )
    db.session.commit()

    response = client.get("/inventory/export.csv")

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment" in response.headers["Content-Disposition"]
    assert "inventory-" in response.headers["Content-Disposition"]
    body = response.get_data(as_text=True)
    assert "asset_number" in body.splitlines()[0]
    assert "EXP-001" in body
    assert "EXP-002" in body


def test_export_assets_csv_applies_filters(app, logged_in_client):
    client, user = logged_in_client
    db.session.add_all(
        [
            Inventory(asset_number="EXP-AVAIL", status=AssetStatus.AVAILABLE),
            Inventory(asset_number="EXP-ASSIGN", status=AssetStatus.ASSIGNED),
        ]
    )
    db.session.commit()

    response = client.get("/inventory/export.csv?status=Available")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "EXP-AVAIL" in body
    assert "EXP-ASSIGN" not in body


def test_list_assets_renders_sortable_headers_and_assigned_to_search(
    app, logged_in_client
):
    client, user = logged_in_client
    asset = Inventory(
        asset_number="ASSIGNED-TAG",
        status=AssetStatus.ASSIGNED,
        assigned_to_user_id=user.id,
    )
    db.session.add(asset)
    db.session.commit()

    response = client.get(
        "/inventory/?assigned_to=Test&sort_by=assigned_to&sort_dir=asc"
    )

    assert response.status_code == 200
    assert b'name="assigned_to"' in response.data
    assert b'value="Test"' in response.data
    assert b"sort_by=asset_number" in response.data
    assert b"ASSIGNED-TAG" in response.data
