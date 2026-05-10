import json
import logging
import os

from flask import Flask, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_migrate import upgrade as migrate_upgrade
from flask_wtf.csrf import CSRFProtect

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
from app.blueprints.inventory.routes import inventory_bp


csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
migrate = Migrate()


class _CloudJsonFormatter(logging.Formatter):
    _SKIP = frozenset({
        "name", "msg", "args", "levelname", "levelno", "pathname",
        "filename", "module", "exc_info", "exc_text", "stack_info",
        "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process", "message",
        "taskName",
    })

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        for key, val in record.__dict__.items():
            if key not in self._SKIP:
                payload[key] = val
        return json.dumps(payload, default=str)


_MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "migrations"
)


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    )

    settings = load_settings()
    startup_issues = validate_production_settings(settings)
    database_startup_issue = any("DATABASE_URL" in issue for issue in startup_issues)
    effective_database_uri = settings.database_url or "sqlite:///lifecycle.db"
    if database_startup_issue:
        effective_database_uri = "sqlite:///lifecycle-maintenance.db"

    engine_options: dict = {
        "pool_pre_ping": True,
        "pool_recycle": settings.pool_recycle,
        "max_overflow": settings.pool_max_overflow,
    }
    if effective_database_uri.startswith("postgresql+pg8000://"):
        engine_options["connect_args"] = {"timeout": 3}
    elif effective_database_uri.startswith("postgresql://"):
        engine_options["connect_args"] = {"connect_timeout": 3}

    is_test = settings.app_env == "test"

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
        POSTMARK_ONBOARDING_MESSAGE_STREAM=settings.postmark_onboarding_message_stream,
        HR_CC_EMAILS=settings.hr_cc_emails,
        FSI_OPS_EMAIL=settings.fsi_ops_email,
        STELLAR_SUPPORT_EMAIL=settings.stellar_support_email,
        STELLAR_SALES_EMAIL=settings.stellar_sales_email,
        INTERNAL_CRON_SHARED_SECRET=settings.internal_cron_shared_secret,
        STARTUP_ISSUES=startup_issues,
        # CSRF & session security
        WTF_CSRF_ENABLED=not is_test,
        WTF_CSRF_TIME_LIMIT=3600,
        SESSION_COOKIE_SECURE=settings.fsi_production,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Inventory / storage
        ASSET_PHOTOS_BUCKET=settings.asset_photos_bucket,
        MAIL_SUPPRESS_SEND=settings.mail_suppress_send,
        MIGRATE_ON_STARTUP=os.getenv("MIGRATE_ON_STARTUP", "false").strip().lower()
        in {"1", "true", "yes"},
        # Rate limiting
        RATELIMIT_ENABLED=not is_test,
    )

    # Structured JSON logging for Cloud Logging in production
    if settings.fsi_production:
        handler = logging.StreamHandler()
        handler.setFormatter(_CloudJsonFormatter())
        app.logger.handlers = [handler]
        app.logger.setLevel(logging.INFO)

    db.init_app(app)
    migrate.init_app(app, db, directory=_MIGRATIONS_DIR)
    csrf.init_app(app)
    limiter.init_app(app)

    # Webhooks and internal cron use their own auth; exempt from CSRF
    csrf.exempt(webhooks_bp)
    csrf.exempt(internal_bp)

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
    app.register_blueprint(inventory_bp, url_prefix="/inventory")

    def _error_response(code: int, title: str, message: str):
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify({"error": title, "message": message}), code
        return (
            render_template(
                "error.html",
                error_code=code,
                error_title=title,
                error_message=message,
            ),
            code,
        )

    @app.errorhandler(401)
    def unauthorized(e):
        return _error_response(401, "Unauthorized", "You must be logged in to access this page.")

    @app.errorhandler(403)
    def forbidden(e):
        return _error_response(403, "Forbidden", "You do not have permission to access this resource.")

    @app.errorhandler(404)
    def not_found(e):
        return _error_response(404, "Not Found", "The page you are looking for does not exist.")

    @app.errorhandler(429)
    def rate_limited(e):
        return _error_response(429, "Too Many Requests", "You have made too many requests. Please slow down.")

    @app.errorhandler(500)
    def internal_error(e):
        return _error_response(
            500, "Internal Server Error", "An unexpected error occurred. Please try again later."
        )

    if app.config.get("MIGRATE_ON_STARTUP"):
        with app.app_context():
            migrate_upgrade()

    return app
