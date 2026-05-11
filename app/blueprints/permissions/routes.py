from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from app.models import DistributionList, FileSharePermission, RoleMatrix, db
from app.services import permission_service


permissions_bp = Blueprint("permissions", __name__)


def _require_admin() -> None:
    user = getattr(g, "current_user", None)
    if user is None:
        abort(401)
    if not getattr(user, "can_manage_lifecycle", False):
        abort(403)


@permissions_bp.get("/matrix")
def matrix():
    _require_admin()
    roles = permission_service.list_role_assignments()
    dls = permission_service.list_active_distribution_lists()
    shares = permission_service.list_active_file_shares()
    return render_template("permissions/matrix.html", roles=roles, distribution_lists=dls, file_shares=shares)


@permissions_bp.get("/distribution-lists")
def distribution_lists():
    _require_admin()
    records = db.session.query(DistributionList).order_by(DistributionList.name.asc()).all()
    return render_template("permissions/distribution_lists.html", records=records)


@permissions_bp.post("/distribution-lists")
def create_distribution_list():
    _require_admin()
    permission_service.create_distribution_list(request.form)
    flash("Distribution list created.", "success")
    return redirect(url_for("permissions.distribution_lists"))


@permissions_bp.get("/file-shares")
def file_shares():
    _require_admin()
    records = db.session.query(FileSharePermission).order_by(FileSharePermission.name.asc()).all()
    return render_template("permissions/file_shares.html", records=records)


@permissions_bp.post("/file-shares")
def create_file_share():
    _require_admin()
    permission_service.create_file_share(request.form)
    flash("File share permission created.", "success")
    return redirect(url_for("permissions.file_shares"))


@permissions_bp.post("/assignments/toggle")
def toggle_assignment():
    _require_admin()
    role_id = request.form.get("role_id", type=int)
    target_id = request.form.get("target_id", type=int)
    assignment_type = (request.form.get("assignment_type") or "").strip()
    enabled = request.form.get("enabled") == "1"

    role = db.session.get(RoleMatrix, role_id)
    if role is None:
        abort(404)

    if assignment_type == "distribution_list":
        target = db.session.get(DistributionList, target_id)
        if target is None:
            abort(404)
        if enabled:
            permission_service.set_distribution_list_assignment(role, target)
        else:
            permission_service.unset_distribution_list_assignment(role, target)
    elif assignment_type == "file_share":
        target = db.session.get(FileSharePermission, target_id)
        if target is None:
            abort(404)
        if enabled:
            permission_service.set_file_share_assignment(role, target)
        else:
            permission_service.unset_file_share_assignment(role, target)
    else:
        abort(400)

    return redirect(url_for("permissions.matrix"))
