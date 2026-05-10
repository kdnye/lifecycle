from __future__ import annotations

from typing import Optional

from sqlalchemy import or_

from app.models import AssetCategory, AssetStatus, Inventory, db


def get_asset_by_id(asset_id: int) -> Optional[Inventory]:
    return db.session.get(Inventory, asset_id)


def get_asset_by_tag(tag_value: str) -> Optional[Inventory]:
    """Search asset_tag, serial_number, and ble_tag_id fields."""
    return Inventory.query.filter(
        or_(
            Inventory.asset_tag == tag_value,
            Inventory.serial_number == tag_value,
            Inventory.ble_tag_id == tag_value,
        )
    ).first()


def _get_category_subtree_ids(root_id: int) -> list[int]:
    """Return root_id plus all descendant category IDs."""
    result = [root_id]
    queue = [root_id]
    while queue:
        parent_ids = queue[:]
        queue = []
        children = AssetCategory.query.filter(
            AssetCategory.parent_category_id.in_(parent_ids)
        ).all()
        for child in children:
            result.append(child.id)
            queue.append(child.id)
    return result


def list_assets(
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 25,
):
    """Return paginated inventory. category_id filter includes all subcategories."""
    query = Inventory.query

    if category_id is not None:
        ids = _get_category_subtree_ids(category_id)
        query = query.filter(Inventory.category_id.in_(ids))

    if status:
        try:
            query = query.filter(Inventory.status == AssetStatus(status))
        except ValueError:
            pass

    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                Inventory.asset_tag.ilike(term),
                Inventory.serial_number.ilike(term),
                Inventory.make.ilike(term),
                Inventory.model_name.ilike(term),
                Inventory.notes.ilike(term),
            )
        )

    return query.order_by(Inventory.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


def create_asset(data: dict) -> Inventory:
    asset = Inventory(
        serial_number=data.get("serial_number") or None,
        asset_tag=data.get("asset_tag") or None,
        ble_tag_id=data.get("ble_tag_id") or None,
        category_id=data.get("category_id") or None,
        make=data.get("make") or None,
        model_name=data.get("model_name") or None,
        status=AssetStatus(data.get("status", "Available")),
        assigned_to_user_id=data.get("assigned_to_user_id") or None,
        photo_url=data.get("photo_url") or None,
        notes=data.get("notes") or None,
        purchase_date=data.get("purchase_date") or None,
        purchase_price=data.get("purchase_price") or None,
        warranty_expiry=data.get("warranty_expiry") or None,
        intake_request_id=data.get("intake_request_id") or None,
    )
    db.session.add(asset)
    db.session.commit()
    return asset


def update_asset(asset: Inventory, data: dict) -> Inventory:
    field_map = [
        "serial_number", "asset_tag", "ble_tag_id",
        "category_id", "make", "model_name",
        "assigned_to_user_id", "photo_url", "notes",
        "purchase_date", "purchase_price", "warranty_expiry",
    ]
    for field in field_map:
        if field in data:
            setattr(asset, field, data[field] or None)
    if "status" in data:
        asset.status = AssetStatus(data["status"])
    db.session.commit()
    return asset


def assign_asset(asset: Inventory, user_id: int) -> Inventory:
    asset.assigned_to_user_id = user_id
    asset.status = AssetStatus.ASSIGNED
    db.session.commit()
    return asset


def unassign_asset(asset: Inventory) -> Inventory:
    asset.assigned_to_user_id = None
    asset.status = AssetStatus.AVAILABLE
    db.session.commit()
    return asset


def retire_asset(asset: Inventory) -> Inventory:
    asset.assigned_to_user_id = None
    asset.status = AssetStatus.RETIRED
    db.session.commit()
    return asset


def list_categories(active_only: bool = True) -> list[AssetCategory]:
    query = AssetCategory.query
    if active_only:
        query = query.filter(AssetCategory.is_active.is_(True))
    return query.order_by(AssetCategory.name).all()


def get_category_tree() -> list[dict]:
    """Return top-level active categories with nested children."""
    all_cats = list_categories(active_only=True)
    by_parent: dict = {}
    for cat in all_cats:
        by_parent.setdefault(cat.parent_category_id, []).append(cat)

    def _build(parent_id):
        return [
            {"category": cat, "children": _build(cat.id)}
            for cat in by_parent.get(parent_id, [])
        ]

    return _build(None)


def create_category(
    name: str, parent_id: Optional[int] = None
) -> AssetCategory:
    cat = AssetCategory(name=name, parent_category_id=parent_id)
    db.session.add(cat)
    db.session.commit()
    return cat


def deactivate_category(category: AssetCategory) -> AssetCategory:
    category.is_active = False
    db.session.commit()
    return category
