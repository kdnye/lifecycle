import pytest
from app.models import AssetStatus, Inventory, db


def test_list_assets_requires_login(client):
    response = client.get("/inventory/")
    assert response.status_code == 302


def test_list_assets_authenticated(app, logged_in_client):
    client, user = logged_in_client
    asset = Inventory(asset_tag="TAG-001", status=AssetStatus.AVAILABLE)
    db.session.add(asset)
    db.session.commit()

    response = client.get("/inventory/")
    assert response.status_code == 200
    assert b"TAG-001" in response.data


def test_asset_detail(app, logged_in_client):
    client, user = logged_in_client
    asset = Inventory(asset_tag="TAG-002", make="Dell", status=AssetStatus.AVAILABLE)
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
            "asset_tag": "NEW-TAG",
            "it_asset_number": "IT-0001",
            "serial_number": "SN-NEW",
            "status": "Available",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    asset = Inventory.query.filter_by(it_asset_number="IT-0001").first()
    assert asset is not None
    assert asset.status == AssetStatus.AVAILABLE
    assert asset.asset_tag == "NEW-TAG"


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
    asset = Inventory(asset_tag="SCAN-TAG", status=AssetStatus.AVAILABLE)
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


def test_archive_asset(app, logged_in_client):
    client, user = logged_in_client
    asset = Inventory(asset_tag="ARCH-TAG", status=AssetStatus.AVAILABLE)
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
