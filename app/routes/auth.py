from __future__ import annotations

from urllib.parse import urlparse

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from app.auth_utils import clear_authenticated_user, get_current_user, set_authenticated_user
from app.models import User

auth_bp = Blueprint("auth", __name__)


def _is_safe_next_url(next_url: str | None) -> bool:
    if not next_url:
        return False
    parsed = urlparse(next_url)
    if parsed.scheme or parsed.netloc:
        return False
    return parsed.path.startswith("/")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    current_user = get_current_user()
    if request.method == "GET":
        if current_user is not None:
            return redirect(url_for("dashboard.index"))
        return render_template("auth/login.html")

    is_json_request = request.is_json
    if is_json_request:
        payload = request.get_json(silent=True) or {}
        email = str(payload.get("email", "")).strip().lower()
    else:
        email = str(request.form.get("email", "")).strip().lower()

    if not email:
        message = "Email is required."
        remediation = "Provide a valid account email."
        if is_json_request:
            return jsonify({"status": "error", "message": message, "remediation": remediation}), 400
        return render_template("auth/login.html", error_message=message), 400

    user = User.query.filter_by(email=email).first()
    if user is None:
        message = "User not found."
        remediation = "Use a registered lifecycle-management account or ask an admin to provision access."
        if is_json_request:
            return jsonify({"status": "error", "message": message, "remediation": remediation}), 404
        return render_template("auth/login.html", error_message=message), 404

    if not user.can_manage_lifecycle:
        message = "Unauthorized. You do not have permissions to manage employee lifecycles."
        remediation = "Request can_manage_lifecycle access from an administrator, then log in again."
        if is_json_request:
            return jsonify({"status": "error", "message": message, "remediation": remediation}), 403
        return render_template("auth/login.html", error_message=message), 403

    set_authenticated_user(user)

    if is_json_request:
        return jsonify({"status": "success", "message": "Logged in.", "user_id": user.id})

    next_page = request.args.get("next")
    if not _is_safe_next_url(next_page):
        next_page = url_for("dashboard.index")
    return redirect(next_page)


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    clear_authenticated_user()
    if request.is_json:
        return jsonify({"status": "success", "message": "Logged out."})
    return redirect(url_for("auth.login"))


@auth_bp.get("/me")
def me():
    user = get_current_user()
    if user is None:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Not authenticated.",
                    "remediation": "Call /login with your lifecycle-management email, then retry /me.",
                }
            ),
            401,
        )

    return jsonify(
        {
            "status": "success",
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
            },
        }
    )
