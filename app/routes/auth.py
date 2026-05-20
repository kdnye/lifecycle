from __future__ import annotations

from urllib.parse import urlparse

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, ValidationError

try:
    from flask_babel import lazy_gettext as _
except ImportError:
    _ = lambda value: value

from app.auth_utils import clear_authenticated_user, get_current_user, set_authenticated_user
from app.services.authentication import authenticate_user
from sqlalchemy.exc import SQLAlchemyError

auth_bp = Blueprint("auth", __name__)




def _validate_email_format(form, field):
    value = str(field.data or "").strip()
    try:
        local_part, domain_part = value.split('@')
    except ValueError:
        # Handles no '@' or more than one '@'
        raise ValidationError("Please provide a valid email address.")

    if not local_part or not domain_part:
        # Handles email starting or ending with '@'
        raise ValidationError("Please provide a valid email address.")

    if '.' not in domain_part or domain_part.startswith('.') or domain_part.endswith('.'):
        raise ValidationError("Please provide a valid email address.")


class LoginForm(FlaskForm):
    email = StringField(_("Email Address"), validators=[DataRequired(), _validate_email_format])
    password = PasswordField(_("Password"), validators=[DataRequired()])
    submit = SubmitField(_("Sign In"))


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
    form = LoginForm()

    if request.method == "GET" and current_user is not None:
        return redirect(url_for("dashboard.index"))

    is_json_request = request.is_json
    if is_json_request:
        payload = request.get_json(silent=True) or {}
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", ""))
    else:
        email = str(form.email.data or "").strip().lower()
        password = str(form.password.data or "")

    if request.method == "POST":
        if is_json_request:
            if not email or not password:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Email and password are required.",
                            "remediation": "Provide valid account credentials and try again.",
                        }
                    ),
                    400,
                )
        elif not form.validate_on_submit():
            return render_template("auth/login.html", form=form), 400

        try:
            principal = authenticate_user(email=email, raw_password=password)
        except SQLAlchemyError:
            current_app.logger.exception("login_user_lookup_failed")
            message = _("Authentication service is temporarily unavailable.")
            remediation = _("Verify shared users schema and database connectivity, then retry.")
            if is_json_request:
                return jsonify({"status": "error", "message": message, "remediation": remediation}), 503
            flash(message, "error")
            return render_template("auth/login.html", form=form), 503

        if principal is None:
            message = "Invalid email or password. Please try again."
            remediation = "Use your registered account credentials or contact an administrator."
            if is_json_request:
                return jsonify({"status": "error", "message": message, "remediation": remediation}), 401
            flash(message, "error")
            return render_template("auth/login.html", form=form), 401

        if not principal.can_manage_lifecycle:
            message = "Unauthorized. You do not have permissions to manage employee lifecycles."
            remediation = "Request can_manage_lifecycle access from an administrator, then log in again."
            if is_json_request:
                return jsonify({"status": "error", "message": message, "remediation": remediation}), 403
            flash(message, "error")
            return render_template("auth/login.html", form=form), 403

        set_authenticated_user(principal.user_id)

        if is_json_request:
            return jsonify({"status": "success", "message": "Logged in.", "user_id": principal.user_id})

        next_page = request.args.get("next")
        if not _is_safe_next_url(next_page):
            next_page = url_for("dashboard.index")
        return redirect(next_page)

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    clear_authenticated_user()
    if request.is_json:
        return jsonify({"status": "success", "message": "Logged out."})
    flash("You have been successfully logged out.", "info")
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
                    "remediation": "Call /login with your lifecycle-management credentials, then retry /me.",
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
