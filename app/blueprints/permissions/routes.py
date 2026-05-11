from flask import (
    Blueprint,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.auth_utils import login_required
from app.models import DistributionList, FileSharePermission, RoleMatrix, User
from app.services import permission_service

permissions_bp = Blueprint("permissions", __name__)


def _require_admin() -> None:
    from app.models import db
    user = db.session.get(User, session.get("fsi_user_id"))
    if not user or not user.can_manage_lifecycle:
        abort(403)


@permissions_bp.get("/")
@login_required
def matrix():
    _require_admin()
    roles = RoleMatrix.query.order_by(RoleMatrix.role_profile).all()
    dls = permission_service.list_distribution_lists(active_only=True)
    shares = permission_service.list_file_shares(active_only=True)
    assignments = permission_service.get_role_assignments()
    return render_template(
        "permissions/matrix.html",
        roles=roles,
        distribution_lists=dls,
        file_shares=shares,
        assignments=assignments,
    )


@permissions_bp.post("/role-assignments")
@login_required
def toggle_role_assignment():
    _require_admin()
    body = request.get_json(silent=True) or {}
    item_type = body.get("type")
    item_id = int(body.get("item_id", 0))
    role_matrix_id = int(body.get("role_matrix_id", 0))
    assigned = bool(body.get("assigned", False))

    if item_type == "distribution_list":
        permission_service.set_role_dl_assignment(role_matrix_id, item_id, assigned)
    elif item_type == "file_share":
        permission_service.set_role_share_assignment(role_matrix_id, item_id, assigned)
    else:
        return jsonify({"error": "invalid type"}), 400

    return "", 204


@permissions_bp.get("/distribution-lists")
@login_required
def list_distribution_lists():
    _require_admin()
    dls = permission_service.list_distribution_lists(active_only=False)
    return render_template("permissions/distribution_lists.html", distribution_lists=dls)


@permissions_bp.post("/distribution-lists")
@login_required
def create_distribution_list():
    _require_admin()
    permission_service.create_distribution_list(request.form.to_dict())
    return redirect(url_for("permissions.list_distribution_lists"))


@permissions_bp.post("/distribution-lists/<int:dl_id>/edit")
@login_required
def update_distribution_list(dl_id: int):
    _require_admin()
    dl = DistributionList.query.get_or_404(dl_id)
    permission_service.update_distribution_list(dl, request.form.to_dict())
    return redirect(url_for("permissions.list_distribution_lists"))


@permissions_bp.post("/distribution-lists/<int:dl_id>/delete")
@login_required
def delete_distribution_list(dl_id: int):
    _require_admin()
    dl = DistributionList.query.get_or_404(dl_id)
    permission_service.deactivate_distribution_list(dl)
    return redirect(url_for("permissions.list_distribution_lists"))


@permissions_bp.get("/file-shares")
@login_required
def list_file_shares():
    _require_admin()
    shares = permission_service.list_file_shares(active_only=False)
    return render_template("permissions/file_shares.html", file_shares=shares)


@permissions_bp.post("/file-shares")
@login_required
def create_file_share():
    _require_admin()
    permission_service.create_file_share(request.form.to_dict())
    return redirect(url_for("permissions.list_file_shares"))


@permissions_bp.post("/file-shares/<int:share_id>/edit")
@login_required
def update_file_share(share_id: int):
    _require_admin()
    share = FileSharePermission.query.get_or_404(share_id)
    permission_service.update_file_share(share, request.form.to_dict())
    return redirect(url_for("permissions.list_file_shares"))


@permissions_bp.post("/file-shares/<int:share_id>/delete")
@login_required
def delete_file_share(share_id: int):
    _require_admin()
    share = FileSharePermission.query.get_or_404(share_id)
    permission_service.deactivate_file_share(share)
    return redirect(url_for("permissions.list_file_shares"))
