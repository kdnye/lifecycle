from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from app.auth_utils import login_required
from app.models import AssetStatus
from app.services import inventory_service
from app.services.asset_storage import delete_asset_photo, upload_asset_photo


inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.get("/")
@login_required
def list_assets():
    category_id = request.args.get("category_id", type=int)
    status = request.args.get("status")
    search = request.args.get("q")
    page = request.args.get("page", 1, type=int)
    pagination = inventory_service.list_assets(
        category_id=category_id,
        status=status,
        search=search,
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
        AssetStatus=AssetStatus,
    )


@inventory_bp.get("/new")
@login_required
def new_asset_form():
    categories = inventory_service.list_categories_hierarchical()
    return render_template(
        "inventory/form.html",
        asset=None,
        categories=categories,
        statuses=list(AssetStatus),
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
    return render_template(
        "inventory/form.html",
        asset=asset,
        categories=categories,
        statuses=list(AssetStatus),
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
    return jsonify({
        "found": True,
        "id": asset.id,
        "asset_tag": asset.asset_tag,
        "serial_number": asset.serial_number,
        "make": asset.make,
        "model_name": asset.model_name,
        "status": asset.status.value,
        "detail_url": url_for("inventory.asset_detail", asset_id=asset.id),
    }), 200


def _asset_data_from_form(form) -> dict:
    return {
        "serial_number": form.get("serial_number", "").strip() or None,
        "asset_tag": form.get("asset_tag", "").strip() or None,
        "ble_tag_id": form.get("ble_tag_id", "").strip() or None,
        "category_id": form.get("category_id", type=int),
        "make": form.get("make", "").strip() or None,
        "model_name": form.get("model_name", "").strip() or None,
        "status": form.get("status", "Available"),
        "assigned_to_user_id": form.get("assigned_to_user_id", type=int),
        "notes": form.get("notes", "").strip() or None,
        "purchase_date": form.get("purchase_date") or None,
        "purchase_price": form.get("purchase_price") or None,
        "warranty_expiry": form.get("warranty_expiry") or None,
    }
