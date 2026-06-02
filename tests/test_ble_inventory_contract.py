from app.models import AssetStatus, AssetTrackingMode, Inventory


def test_ble_inventory_contract_matches_dashboard_ingestion_strings():
    ble_column = Inventory.__table__.c.ble_tag_id

    assert ble_column.type.length == 100
    assert ble_column.nullable is True
    assert ble_column.unique is True
    assert ble_column.index is True
    assert AssetTrackingMode.SERIALIZED.value == "Serialized"
    assert AssetStatus.ASSIGNED.value == "Assigned"
    assert AssetStatus.AVAILABLE.value == "Available"
