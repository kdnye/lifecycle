import csv
import io
from datetime import datetime, timezone

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    stream_with_context,
    url_for,
)

from app.auth_utils import login_required
from app.models import AssetStatus, AssetTrackingMode, db
from app.services import inventory_service
from app.services.asset_storage import delete_asset_photo, upload_asset_photo

inventory_bp = Blueprint("inventory", __name__)

_EXPORT_COLUMNS = [
    "id",
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
    "assigned_to_name",
    "assigned_to_email",
    "location",
    "purchase_date",
    "purchase_price",
    "warranty_expiry",
    "notes",
    "created_at",
    "updated_at",
]


def _asset_to_row(asset) -> list:
    category_name = ""
    if asset.category is not None:
        parent = asset.category.parent
        category_name = (
            f"{parent.name}: {asset.category.name}" if parent else asset.category.name
        )
    assigned_name = ""
    assigned_email = ""
    if asset.assigned_to is not None:
        assigned_name = (
            asset.assigned_to.name
            or " ".join(
                part
                for part in [asset.assigned_to.first_name, asset.assigned_to.last_name]
                if part
            )
            or ""
        )
        assigned_email = asset.assigned_to.email or ""
    return [
        asset.id,
        asset.asset_number or "",
        asset.it_asset_tag or "",
        asset.serial_number or "",
        asset.ble_tag_id or "",
        category_name,
        asset.make or "",
        asset.model_name or "",
        asset.tracking_mode.value if asset.tracking_mode else "",
        asset.quantity if asset.quantity is not None else "",
        asset.status.value if asset.status else "",
        assigned_name,
        assigned_email,
        asset.location or "",
        asset.purchase_date.isoformat() if asset.purchase_date else "",
        f"{asset.purchase_price:.2f}" if asset.purchase_price is not None else "",
        asset.warranty_expiry.isoformat() if asset.warranty_expiry else "",
        asset.notes or "",
        asset.created_at.isoformat() if asset.created_at else "",
        asset.updated_at.isoformat() if asset.updated_at else "",
    ]


@inventory_bp.get("/")
@login_required
def list_assets():
    category_id = request.args.get("category_id", type=int)
    status = request.args.get("status")
    search = request.args.get("q")
    assigned_to_search = request.args.get("assigned_to")
    sort_by = request.args.get("sort_by", "id")
    sort_dir = request.args.get("sort_dir", "desc")
    page = request.args.get("page", 1, type=int)
    pagination = inventory_service.list_assets(
        category_id=category_id,
        status=status,
        search=search,
        assigned_to=assigned_to_search,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        per_page=25,
    )
    categories = inventory_service.get_category_tree()
    return render_template(
        "inventory/list.html",
        pagination=pagination,
        assets=pagination.items,
        categories=categories,
        selected_category_id=category_id,
        selected_status=status,
        search=search,
        assigned_to_search=assigned_to_search,
        sort_by=sort_by,
        sort_dir=sort_dir,
        AssetStatus=AssetStatus,
    )


@inventory_bp.get("/export.csv")
@login_required
def export_assets_csv():
    category_id = request.args.get("category_id", type=int)
    status = request.args.get("status")
    search = request.args.get("q")
    assigned_to_search = request.args.get("assigned_to")
    sort_by = request.args.get("sort_by", "id")
    sort_dir = request.args.get("sort_dir", "desc")

    assets = inventory_service.iter_assets_for_export(
        category_id=category_id,
        status=status,
        search=search,
        assigned_to=assigned_to_search,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    def generate():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(_EXPORT_COLUMNS)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        for asset in assets:
            writer.writerow(_asset_to_row(asset))
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    filename = f"inventory-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.csv"
    return Response(
        stream_with_context(generate()),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@inventory_bp.get("/new")
@login_required
def new_asset_form():
    categories = inventory_service.list_categories_hierarchical()
    assignable_users = inventory_service.list_assignable_users()
    prefill_asset_number = request.args.get("asset_number", "").strip()
    return render_template(
        "inventory/form.html",
        asset=None,
        prefill_asset_number=prefill_asset_number,
        categories=categories,
        statuses=list(AssetStatus),
        tracking_modes=list(AssetTrackingMode),
        assignable_users=assignable_users,
    )


@inventory_bp.post("/new")
@login_required
def create_asset():
    data = _asset_data_from_form(request.form)
    try:
        asset = inventory_service.create_asset(data)
    except Exception as exc:
        flash(str(exc), "danger")
        return redirect(url_for("inventory.new_asset_form"))
    flash("Asset created.", "success")
    return redirect(url_for("inventory.asset_detail", asset_id=asset.id))


@inventory_bp.get("/<int:asset_id>")
@login_required
def asset_detail(asset_id: int):
    asset = inventory_service.get_asset_by_id(asset_id)
    if asset is None:
        abort(404)
    return render_template("inventory/detail.html", asset=asset)


@inventory_bp.get("/<int:asset_id>/edit")
@login_required
def edit_asset_form(asset_id: int):
    asset = inventory_service.get_asset_by_id(asset_id)
    if asset is None:
        abort(404)
    categories = inventory_service.list_categories_hierarchical()
    assignable_users = inventory_service.list_assignable_users()
    return render_template(
        "inventory/form.html",
        asset=asset,
        categories=categories,
        statuses=list(AssetStatus),
        tracking_modes=list(AssetTrackingMode),
        assignable_users=assignable_users,
    )


@inventory_bp.post("/<int:asset_id>/edit")
@login_required
def update_asset(asset_id: int):
    asset = inventory_service.get_asset_by_id(asset_id)
    if asset is None:
        abort(404)
    data = _asset_data_from_form(request.form)
    try:
        inventory_service.update_asset(asset, data)
    except Exception as exc:
        flash(str(exc), "danger")
        return redirect(url_for("inventory.edit_asset_form", asset_id=asset_id))
    flash("Asset updated.", "success")
    return redirect(url_for("inventory.asset_detail", asset_id=asset_id))


@inventory_bp.post("/<int:asset_id>/photo")
@login_required
def upload_photo(asset_id: int):
    asset = inventory_service.get_asset_by_id(asset_id)
    if asset is None:
        abort(404)
    file = request.files.get("photo")
    if not file or not file.filename:
        flash("No file selected.", "warning")
        return redirect(url_for("inventory.asset_detail", asset_id=asset_id))
    try:
        if asset.photo_url:
            delete_asset_photo(asset.photo_url)
        photo_url = upload_asset_photo(file, asset_id)
        inventory_service.update_asset(asset, {"photo_url": photo_url})
        flash("Photo uploaded.", "success")
    except (ValueError, RuntimeError) as exc:
        flash(str(exc), "danger")
    return redirect(url_for("inventory.asset_detail", asset_id=asset_id))


@inventory_bp.post("/<int:asset_id>/archive")
@login_required
def archive_asset(asset_id: int):
    asset = inventory_service.get_asset_by_id(asset_id)
    if asset is None:
        abort(404)
    inventory_service.retire_asset(asset)
    flash("Asset archived (status: Retired).", "success")
    return redirect(url_for("inventory.list_assets"))


@inventory_bp.get("/categories")
@login_required
def list_categories():
    tree = inventory_service.get_category_tree()
    all_cats = inventory_service.list_categories(active_only=False)
    return render_template(
        "inventory/categories.html",
        tree=tree,
        all_categories=all_cats,
    )


@inventory_bp.post("/categories/new")
@login_required
def create_category():
    name = request.form.get("name", "").strip()
    parent_id = request.form.get("parent_id", type=int)
    if not name:
        flash("Category name is required.", "warning")
        return redirect(url_for("inventory.list_categories"))
    inventory_service.create_category(name, parent_id)
    flash(f"Category '{name}' created.", "success")
    return redirect(url_for("inventory.list_categories"))


@inventory_bp.get("/audit")
@login_required
def audit_mode():
    """Renders the single-scan Inventory Mode."""
    return render_template("inventory/audit.html")


@inventory_bp.post("/audit/link")
@login_required
def link_fsi_to_it_tag():
    """Form submission to link a scanned FSI number to an existing IT Tag."""
    fsi_number = request.form.get("fsi_number", "").strip()
    it_asset_tag = request.form.get("it_asset_tag", "").strip()

    if not fsi_number or not it_asset_tag:
        flash("Both FSI Number and IT Asset Tag are required.", "danger")
        return redirect(url_for("inventory.audit_mode"))

    existing_fsi_asset = inventory_service.get_asset_by_tag(fsi_number)
    if existing_fsi_asset:
        flash(
            f"FSI Number '{fsi_number}' is already linked to another asset.", "danger"
        )
        return redirect(url_for("inventory.audit_mode"))

    asset = inventory_service.get_asset_by_tag(it_asset_tag)
    if not asset:
        flash(f"IT Asset Tag '{it_asset_tag}' not found.", "danger")
        return redirect(url_for("inventory.audit_mode"))

    try:
        inventory_service.update_asset(asset, {"asset_number": fsi_number})
        flash(f"Linked {fsi_number} to existing asset.", "success")
        return redirect(url_for("inventory.edit_asset_form", asset_id=asset.id))
    except Exception as exc:
        db.session.rollback()
        flash(str(exc), "danger")
        return redirect(url_for("inventory.audit_mode"))


@inventory_bp.post("/scan")
@login_required
def scan_lookup():
    body = request.get_json(silent=True) or {}
    tag = (body.get("tag") or request.form.get("tag", "")).strip()
    if not tag:
        return jsonify({"found": False, "tag": tag}), 200
    asset = inventory_service.get_asset_by_tag(tag)
    if asset is None:
        return jsonify({"found": False, "tag": tag}), 200
    return (
        jsonify(
            {
                "found": True,
                "id": asset.id,
                "asset_number": asset.asset_number,
                "it_asset_tag": asset.it_asset_tag,
                "serial_number": asset.serial_number,
                "make": asset.make,
                "model_name": asset.model_name,
                "status": asset.status.value,
                "detail_url": url_for("inventory.asset_detail", asset_id=asset.id),
            }
        ),
        200,
    )


def _asset_data_from_form(form) -> dict:
    return {
        "serial_number": form.get("serial_number", "").strip() or None,
        "asset_number": form.get("asset_number", "").strip() or None,
        "it_asset_tag": form.get("it_asset_tag", "").strip() or None,
        "ble_tag_id": form.get("ble_tag_id", "").strip() or None,
        "category_id": form.get("category_id", type=int),
        "make": form.get("make", "").strip() or None,
        "model_name": form.get("model_name", "").strip() or None,
        "tracking_mode": form.get("tracking_mode", "Serialized"),
        "quantity": form.get("quantity", type=int),
        "status": form.get("status", "Available"),
        "assigned_to_user_id": form.get("assigned_to_user_id", type=int),
        "location": form.get("location", "").strip() or None,
        "notes": form.get("notes", "").strip() or None,
        "purchase_date": form.get("purchase_date") or None,
        "purchase_price": form.get("purchase_price") or None,
        "warranty_expiry": form.get("warranty_expiry") or None,
    }
