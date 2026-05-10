import pytest
from app.models import AssetCategory, AssetStatus, Inventory, db
from app.services import inventory_service


def test_create_and_retrieve_asset(app):
    asset = inventory_service.create_asset({
        "asset_tag": "SVC-001",
        "make": "Apple",
        "model_name": "MacBook Pro",
        "status": "Available",
    })
    assert asset.id is not None

    retrieved = inventory_service.get_asset_by_id(asset.id)
    assert retrieved is not None
    assert retrieved.asset_tag == "SVC-001"
    assert retrieved.make == "Apple"
    assert retrieved.status == AssetStatus.AVAILABLE


def test_get_asset_by_tag_searches_all_tag_fields(app):
    a1 = Inventory(serial_number="SER-AAA", status=AssetStatus.AVAILABLE)
    a2 = Inventory(asset_tag="TAG-BBB", status=AssetStatus.AVAILABLE)
    a3 = Inventory(ble_tag_id="BLE-CCC", status=AssetStatus.AVAILABLE)
    db.session.add_all([a1, a2, a3])
    db.session.commit()

    assert inventory_service.get_asset_by_tag("SER-AAA") is not None
    assert inventory_service.get_asset_by_tag("TAG-BBB") is not None
    assert inventory_service.get_asset_by_tag("BLE-CCC") is not None
    assert inventory_service.get_asset_by_tag("NOTFOUND") is None


def test_retire_asset_clears_assignment(app):
    asset = Inventory(
        asset_tag="RET-001",
        status=AssetStatus.ASSIGNED,
        assigned_to_user_id=999,
    )
    db.session.add(asset)
    db.session.commit()

    inventory_service.retire_asset(asset)

    assert asset.status == AssetStatus.RETIRED
    assert asset.assigned_to_user_id is None


def test_category_tree_structure(app):
    parent = AssetCategory(name="Computers", is_active=True)
    db.session.add(parent)
    db.session.flush()

    child = AssetCategory(name="Laptops", parent_category_id=parent.id, is_active=True)
    db.session.add(child)
    db.session.commit()

    tree = inventory_service.get_category_tree()
    assert len(tree) == 1
    assert tree[0]["category"].name == "Computers"
    assert len(tree[0]["children"]) == 1
    assert tree[0]["children"][0]["category"].name == "Laptops"
