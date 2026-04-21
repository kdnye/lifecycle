from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.auth_utils import clear_authenticated_user, get_current_user, set_authenticated_user
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip().lower()
    if not email:
        return jsonify({"status": "error", "message": "Email is required."}), 400

    user = User.query.filter_by(email=email).first()
    if user is None:
        return jsonify({"status": "error", "message": "User not found."}), 404

    if not user.can_manage_lifecycle:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Unauthorized. You do not have permissions to manage employee lifecycles.",
                }
            ),
            403,
        )

    set_authenticated_user(user)
    return jsonify({"status": "success", "message": "Logged in.", "user_id": user.id})


@auth_bp.post("/logout")
def logout():
    clear_authenticated_user()
    return jsonify({"status": "success", "message": "Logged out."})


@auth_bp.get("/me")
def me():
    user = get_current_user()
    if user is None:
        return jsonify({"status": "error", "message": "Not authenticated."}), 401

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
