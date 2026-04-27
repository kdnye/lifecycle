import os

from flask import Flask, jsonify, request

from app.config import load_settings, validate_production_settings
from app.auth_utils import attach_current_user
from app.models import db
from app.routes.auth import auth_bp
from app.routes.account import account_bp
from app.routes.dashboard import dashboard_bp
from app.routes.health import health_bp
from app.routes.help import help_bp
from app.routes.intake import intake_bp
from app.routes.internal import internal_bp
from app.routes.webhooks import webhooks_bp


def create_app() -> Flask:
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"))

    settings = load_settings()
    startup_issues = validate_production_settings(settings)
    database_startup_issue = any("DATABASE_URL" in issue for issue in startup_issues)
    effective_database_uri = settings.database_url or "sqlite:///lifecycle.db"
    if database_startup_issue:
        # Keep the process bootable so /healthz and /readyz can return actionable guidance.
        effective_database_uri = "sqlite:///lifecycle-maintenance.db"

    engine_options = {"pool_pre_ping": True}
    if effective_database_uri.startswith("postgresql+pg8000://"):
        engine_options["connect_args"] = {"timeout": 3}
    elif effective_database_uri.startswith("postgresql://"):
        # Keep postgres drivers fail-fast during readiness checks.
        engine_options["connect_args"] = {"connect_timeout": 3}

    app.config.update(
        SECRET_KEY=settings.secret_key or "dev-only-key",
        FSI_PRODUCTION=settings.fsi_production,
        SQLALCHEMY_DATABASE_URI=effective_database_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS=engine_options,
        POSTMARK_SERVER_TOKEN=settings.postmark_server_token,
        POSTMARK_WEBHOOK_TOKEN=settings.postmark_webhook_token,
        DEFAULT_SENDER_EMAIL=settings.default_sender_email,
        MAIL_MESSAGE_STREAM=settings.mail_message_stream,
        HR_CC_EMAILS=settings.hr_cc_emails,
        FSI_OPS_EMAIL=settings.fsi_ops_email,
        STELLAR_SUPPORT_EMAIL=settings.stellar_support_email,
        STELLAR_SALES_EMAIL=settings.stellar_sales_email,
        INTERNAL_CRON_SHARED_SECRET=settings.internal_cron_shared_secret,
        STARTUP_ISSUES=startup_issues,
    )

    db.init_app(app)
    app.before_request(attach_current_user)

    @app.before_request
    def enforce_maintenance_mode():
        issues: list[str] = app.config.get("STARTUP_ISSUES", [])
        if not issues:
            return None

        if request.path in {"/healthz", "/readyz"}:
            return None

        return (
            jsonify(
                {
                    "status": "maintenance",
                    "guidance": "Application configuration is invalid. Resolve startup issues and redeploy.",
                    "issues": issues,
                }
            ),
            503,
        )

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(account_bp)
    app.register_blueprint(intake_bp)
    app.register_blueprint(internal_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(help_bp)
    app.register_blueprint(webhooks_bp)

    return app
