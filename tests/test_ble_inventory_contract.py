import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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

    tracking_mode_column = Inventory.__table__.c.tracking_mode
    status_column = Inventory.__table__.c.status

    assert tracking_mode_column.type.enums == ["Serialized", "Quantity"]
    assert status_column.type.enums == [
        "Available",
        "Assigned",
        "In_Repair",
        "Retired",
        "Lost",
    ]
