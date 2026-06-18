from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from app.models import (
    AssetCategory,
    AssetStatus,
    AssetTrackingMode,
    Inventory,
    User,
    db,
)


def _normalize_ble_tag_id(value: Optional[str]) -> Optional[str]:
    """Canonicalize a BLE tag ID to uppercase alphanumeric (strip separators).

    The smart-trucks edge emitter and the motive-dashboard BLE worker both reduce
    MAC addresses to this form, and the dashboard joins detections to
    ``inventory.ble_tag_id``. Normalizing on write guarantees a colon-formatted MAC
    typed by Ops/HR (e.g. ``E4:5F:01:AA:BB:CC``) matches the detection key.
    """
    if not value:
        return None
    normalized = "".join(ch for ch in str(value) if ch.isalnum()).upper()
    return normalized or None


def _validate_tracking_data(data: dict) -> None:
    tracking_mode = data.get("tracking_mode", AssetTrackingMode.SERIALIZED.value)
    mode_enum = AssetTrackingMode(tracking_mode)
    quantity = data.get("quantity")
    normalized_quantity = int(quantity) if quantity not in (None, "") else 1

    if normalized_quantity < 1:
        raise ValueError("Quantity must be at least 1.")
    if mode_enum == AssetTrackingMode.SERIALIZED and normalized_quantity != 1:
        raise ValueError("Serialized assets must have quantity set to 1.")


def get_asset_by_id(asset_id: int) -> Optional[Inventory]:
    return db.session.get(Inventory, asset_id)


def get_asset_by_tag(tag_value: str) -> Optional[Inventory]:
    """Search asset_number, it_asset_tag, serial_number, and ble_tag_id fields."""
    if not tag_value:
        return None
    ble_tag_id = _normalize_ble_tag_id(tag_value)
    clauses = [
        Inventory.asset_number == tag_value,
        Inventory.it_asset_tag == tag_value,
        Inventory.serial_number == tag_value,
        # Match the raw value too, so legacy rows whose ble_tag_id predates
        # normalization (e.g. stored with colons) remain searchable.
        Inventory.ble_tag_id == tag_value,
    ]
    if ble_tag_id and ble_tag_id != tag_value:
        clauses.append(Inventory.ble_tag_id == ble_tag_id)
    return Inventory.query.filter(or_(*clauses)).first()


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


def _build_asset_query(
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    assigned_to: Optional[str] = None,
    sort_by: str = "id",
    sort_dir: str = "desc",
):
    """Build the filtered+ordered inventory query shared by list and export."""
    query = Inventory.query
    joined_category = False
    joined_user = False

    if category_id is not None:
        ids = _get_category_subtree_ids(category_id)
        query = query.filter(Inventory.category_id.in_(ids))

    if status:
        try:
            query = query.filter(Inventory.status == AssetStatus(status))
        except ValueError:
            pass

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Inventory.asset_number.ilike(term),
                Inventory.it_asset_tag.ilike(term),
                Inventory.serial_number.ilike(term),
                Inventory.make.ilike(term),
                Inventory.model_name.ilike(term),
                Inventory.location.ilike(term),
                Inventory.notes.ilike(term),
            )
        )

    if assigned_to:
        assigned_to = assigned_to.strip()
        if assigned_to.lower() in {"unassigned", "none", "null", "-", "—"}:
            query = query.filter(Inventory.assigned_to_user_id.is_(None))
        elif assigned_to:
            term = f"%{assigned_to}%"
            query = query.join(Inventory.assigned_to)
            joined_user = True
            query = query.filter(
                or_(
                    User.name.ilike(term),
                    User.first_name.ilike(term),
                    User.last_name.ilike(term),
                    User.email.ilike(term),
                )
            )

    sort_key = (sort_by or "id").strip().lower()
    direction = (sort_dir or "desc").strip().lower()
    if direction not in {"asc", "desc"}:
        direction = "desc"

    if sort_key == "category" and not joined_category:
        query = query.outerjoin(Inventory.category)
        joined_category = True
    if sort_key == "assigned_to" and not joined_user:
        query = query.outerjoin(Inventory.assigned_to)
        joined_user = True

    assigned_display_name = func.coalesce(
        User.name,
        User.first_name,
        User.last_name,
        User.email,
        "",
    )
    sort_columns = {
        "asset_number": [Inventory.asset_number, Inventory.id],
        "it_asset_tag": [Inventory.it_asset_tag, Inventory.id],
        "serial_number": [Inventory.serial_number, Inventory.id],
        "category": [AssetCategory.name, Inventory.id],
        "make_model": [Inventory.make, Inventory.model_name, Inventory.id],
        "status": [Inventory.status, Inventory.id],
        "assigned_to": [assigned_display_name, Inventory.id],
        "id": [Inventory.id],
    }
    columns = sort_columns.get(sort_key, sort_columns["id"])
    order_by = [
        column.asc() if direction == "asc" else column.desc() for column in columns
    ]

    return query.order_by(*order_by)


def list_assets(
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    assigned_to: Optional[str] = None,
    sort_by: str = "id",
    sort_dir: str = "desc",
    page: int = 1,
    per_page: int = 25,
):
    """Return paginated inventory with filters and safe column sorting.

    category_id includes all subcategories. assigned_to searches employee
    identity fields so managers can find all equipment assigned to a person.
    """
    return _build_asset_query(
        category_id=category_id,
        status=status,
        search=search,
        assigned_to=assigned_to,
        sort_by=sort_by,
        sort_dir=sort_dir,
    ).paginate(page=page, per_page=per_page, error_out=False)


def iter_assets_for_export(
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    assigned_to: Optional[str] = None,
    sort_by: str = "id",
    sort_dir: str = "desc",
):
    """Yield inventory rows matching the same filters as list_assets.

    Uses ``yield_per`` so large inventories stream without loading every row
    into memory at once.
    """
    query = _build_asset_query(
        category_id=category_id,
        status=status,
        search=search,
        assigned_to=assigned_to,
        sort_by=sort_by,
        sort_dir=sort_dir,
    ).options(
        joinedload(Inventory.category).joinedload(AssetCategory.parent),
        joinedload(Inventory.assigned_to),
    )
    return query.yield_per(200)


def list_assignable_users() -> list[User]:
    """Return active users for assignment dropdown."""
    return (
        User.query.filter(User.is_active.is_(True))
        .order_by(
            User.name.asc(), User.first_name.asc(), User.last_name.asc(), User.id.asc()
        )
        .all()
    )


def create_asset(data: dict) -> Inventory:
    _validate_tracking_data(data)
    asset = Inventory(
        serial_number=data.get("serial_number") or None,
        asset_number=data.get("asset_number") or None,
        it_asset_tag=data.get("it_asset_tag") or None,
        ble_tag_id=_normalize_ble_tag_id(data.get("ble_tag_id")),
        category_id=data.get("category_id") or None,
        make=data.get("make") or None,
        model_name=data.get("model_name") or None,
        tracking_mode=AssetTrackingMode(
            data.get("tracking_mode", AssetTrackingMode.SERIALIZED.value)
        ),
        quantity=int(data.get("quantity") if data.get("quantity") is not None else 1),
        status=AssetStatus(data.get("status", "Available")),
        assigned_to_user_id=data.get("assigned_to_user_id") or None,
        photo_url=data.get("photo_url") or None,
        location=data.get("location") or None,
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
    merged = {
        "tracking_mode": (
            data.get("tracking_mode")
            if "tracking_mode" in data
            else asset.tracking_mode.value
        ),
        "quantity": data.get("quantity") if "quantity" in data else asset.quantity,
    }
    _validate_tracking_data(merged)
    field_map = [
        "serial_number",
        "asset_number",
        "it_asset_tag",
        "ble_tag_id",
        "category_id",
        "make",
        "model_name",
        "assigned_to_user_id",
        "photo_url",
        "location",
        "notes",
        "purchase_date",
        "purchase_price",
        "warranty_expiry",
    ]
    for field in field_map:
        if field in data:
            if field == "ble_tag_id":
                setattr(asset, field, _normalize_ble_tag_id(data[field]))
            else:
                setattr(asset, field, data[field] or None)
    if "tracking_mode" in data:
        asset.tracking_mode = AssetTrackingMode(data["tracking_mode"])
    if "quantity" in data:
        asset.quantity = int(data["quantity"] if data["quantity"] is not None else 1)
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


def list_categories_hierarchical(active_only: bool = True) -> list[dict]:
    """Return categories ordered by hierarchy for dropdown rendering."""
    all_cats = list_categories(active_only=active_only)
    by_parent: dict = {}
    for cat in all_cats:
        by_parent.setdefault(cat.parent_category_id, []).append(cat)

    flattened: list[dict] = []

    def _walk(parent_id: int | None, depth: int) -> None:
        for cat in by_parent.get(parent_id, []):
            flattened.append({"category": cat, "depth": depth})
            _walk(cat.id, depth + 1)

    _walk(None, 0)
    return flattened


def create_category(name: str, parent_id: Optional[int] = None) -> AssetCategory:
    cat = AssetCategory(name=name, parent_category_id=parent_id)
    db.session.add(cat)
    db.session.commit()
    return cat


def deactivate_category(category: AssetCategory) -> AssetCategory:
    category.is_active = False
    db.session.commit()
    return category


# --- CSV import -------------------------------------------------------------

# Columns the importer will write to. `id` is the match key, not a target.
# `created_at`/`updated_at`/`photo_url` are intentionally excluded — timestamps
# are managed by the ORM and photos live in GCS.
_IMPORTABLE_COLUMNS = {
    "asset_number",
    "it_asset_tag",
    "serial_number",
    "ble_tag_id",
    "category",
    "make",
    "model_name",
    "tracking_mode",
    "quantity",
    "status",
    "assigned_to_email",
    "location",
    "purchase_date",
    "purchase_price",
    "warranty_expiry",
    "notes",
}


def _parse_int(value: str) -> Optional[int]:
    value = value.strip()
    if not value:
        return None
    return int(value)


def _parse_decimal(value: str) -> Optional[Decimal]:
    value = value.strip()
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid decimal '{value}'") from exc


def _parse_date(value: str) -> Optional[date]:
    value = value.strip()
    if not value:
        return None
    # Tolerate full ISO datetimes (the export writes plain YYYY-MM-DD, but a
    # user might paste a timestamp from elsewhere).
    return date.fromisoformat(value[:10])


def _resolve_category(value: str, cache: dict) -> Optional[int]:
    """Resolve a 'Parent: Child' or 'Name' string to a category id.

    Empty value clears the category. Unknown names raise ValueError.
    """
    value = value.strip()
    if not value:
        return None
    if value in cache:
        return cache[value]

    if ":" in value:
        parent_name, child_name = (part.strip() for part in value.split(":", 1))
        category = (
            AssetCategory.query.filter(AssetCategory.name == child_name)
            .filter(AssetCategory.parent.has(name=parent_name))
            .first()
        )
    else:
        category = AssetCategory.query.filter(AssetCategory.name == value).first()

    if category is None:
        raise ValueError(f"Unknown category '{value}'")
    cache[value] = category.id
    return category.id


def _resolve_assigned_user(value: str, cache: dict) -> Optional[int]:
    """Resolve an email to a user id. Empty clears assignment."""
    value = value.strip()
    if not value:
        return None
    if value in cache:
        return cache[value]
    user = User.query.filter(func.lower(User.email) == value.lower()).first()
    if user is None:
        raise ValueError(f"Unknown assigned_to_email '{value}'")
    cache[value] = user.id
    return user.id


def _apply_csv_row_to_asset(
    asset: Inventory,
    row: dict,
    columns: set,
    category_cache: dict,
    user_cache: dict,
) -> None:
    """Mutate ``asset`` in place with values from a parsed CSV row."""
    # Resolve string fields first so failures abort before any mutation.
    pending: dict = {}

    for field in (
        "asset_number",
        "it_asset_tag",
        "serial_number",
        "make",
        "model_name",
        "location",
        "notes",
    ):
        if field in columns:
            pending[field] = row.get(field, "").strip() or None

    if "ble_tag_id" in columns:
        pending["ble_tag_id"] = _normalize_ble_tag_id(row.get("ble_tag_id", ""))

    if "tracking_mode" in columns:
        raw = row.get("tracking_mode", "").strip()
        pending["tracking_mode"] = (
            AssetTrackingMode(raw) if raw else AssetTrackingMode.SERIALIZED
        )

    if "quantity" in columns:
        quantity = _parse_int(row.get("quantity", ""))
        pending["quantity"] = quantity if quantity is not None else 1

    if "status" in columns:
        raw = row.get("status", "").strip()
        pending["status"] = AssetStatus(raw) if raw else AssetStatus.AVAILABLE

    if "purchase_date" in columns:
        pending["purchase_date"] = _parse_date(row.get("purchase_date", ""))
    if "warranty_expiry" in columns:
        pending["warranty_expiry"] = _parse_date(row.get("warranty_expiry", ""))
    if "purchase_price" in columns:
        pending["purchase_price"] = _parse_decimal(row.get("purchase_price", ""))

    if "category" in columns:
        pending["category_id"] = _resolve_category(
            row.get("category", ""), category_cache
        )
    if "assigned_to_email" in columns:
        pending["assigned_to_user_id"] = _resolve_assigned_user(
            row.get("assigned_to_email", ""), user_cache
        )

    # Validate the tracking_mode/quantity combo using the resolved values.
    mode = pending.get("tracking_mode", asset.tracking_mode)
    quantity = pending.get("quantity", asset.quantity)
    if quantity is None or quantity < 1:
        raise ValueError("Quantity must be at least 1.")
    if mode == AssetTrackingMode.SERIALIZED and quantity != 1:
        raise ValueError("Serialized assets must have quantity set to 1.")

    for field, value in pending.items():
        setattr(asset, field, value)


def update_assets_from_csv(file_stream) -> dict:
    """Apply updates from an uploaded inventory CSV.

    Matches rows by the ``id`` column. Only columns present in the CSV header
    are written — a blank cell clears that field, an absent column is left
    untouched. The whole import runs in one transaction: if any row fails
    validation the session is rolled back so the user can fix and retry.
    """
    text = file_stream.read()
    if isinstance(text, bytes):
        text = text.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    fieldnames = reader.fieldnames or []
    if "id" not in fieldnames:
        raise ValueError("CSV is missing required 'id' column.")
    writable = {name for name in fieldnames if name in _IMPORTABLE_COLUMNS}

    updated = 0
    skipped = 0
    errors: list[str] = []
    category_cache: dict = {}
    user_cache: dict = {}

    try:
        for line_no, row in enumerate(reader, start=2):  # 1 is the header
            raw_id = (row.get("id") or "").strip()
            if not raw_id:
                skipped += 1
                continue
            try:
                asset_id = int(raw_id)
            except ValueError:
                errors.append(f"Row {line_no}: invalid id '{raw_id}'")
                continue

            asset = db.session.get(Inventory, asset_id)
            if asset is None:
                errors.append(f"Row {line_no}: no asset with id={asset_id}")
                continue

            try:
                _apply_csv_row_to_asset(
                    asset, row, writable, category_cache, user_cache
                )
            except ValueError as exc:
                errors.append(f"Row {line_no}: {exc}")
                continue
            updated += 1

        if errors:
            db.session.rollback()
            return {"updated": 0, "skipped": skipped, "errors": errors}

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return {"updated": updated, "skipped": skipped, "errors": errors}
