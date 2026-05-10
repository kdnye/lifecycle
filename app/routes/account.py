from __future__ import annotations

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from app.auth_utils import clear_authenticated_user
from app.services.communication_options import (
    CommunicationOptionValues,
    get_communication_options,
    save_communication_options,
)

account_bp = Blueprint("account", __name__, url_prefix="/account")


@account_bp.get("/profile")
def profile():
    return render_template("account/profile.html", title="Account Profile")


@account_bp.route("/communication-options", methods=["GET", "POST"])
def communication_options():
    if request.method == "POST":
        values = CommunicationOptionValues(
            it_support_email=str(request.form.get("it_support_email", "")).strip(),
            it_sales_email=str(request.form.get("it_sales_email", "")).strip(),
            telecon_sales_email=str(request.form.get("telecon_sales_email", "")).strip(),
            internal_notification_list=str(request.form.get("internal_notification_list", "")).strip(),
        )
        ok, message = save_communication_options(values)
        flash(message, "success" if ok else "error")
        return redirect(url_for("account.communication_options"))

    options = get_communication_options()
    return render_template(
        "account/communication_options.html",
        title="Communication Options",
        options=options,
    )


@account_bp.post("/theme")
def set_theme():
    """Store theme preference. Lifecycle cannot write to the users table,
    so persistence is localStorage-only; this endpoint returns 200 for
    compatibility with the FSI theme-toggle JS pattern."""
    theme = request.form.get("theme", "light")
    if theme not in ("light", "dark"):
        return jsonify({"error": "invalid theme"}), 400
    return jsonify({"theme": theme}), 200


@account_bp.get("/logout")
def logout():
    clear_authenticated_user()
    return redirect(url_for("dashboard.index"))
