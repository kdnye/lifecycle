import os

from flask import Flask

from app.config import load_settings, validate_production_settings
from app.models import db
from app.routes.health import health_bp
from app.routes.help import help_bp
from app.routes.intake import intake_bp
from app.routes.webhooks import webhooks_bp


def create_app() -> Flask:
    app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"))

    settings = load_settings()
    production_errors = validate_production_settings(settings)
    if production_errors:
        raise RuntimeError(" | ".join(production_errors))

    app.config.update(
        SECRET_KEY=settings.secret_key or "dev-only-key",
        SQLALCHEMY_DATABASE_URI=settings.database_url or "sqlite:///lifecycle.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        POSTMARK_SERVER_TOKEN=settings.postmark_server_token,
        DEFAULT_SENDER_EMAIL=settings.default_sender_email,
        MAIL_MESSAGE_STREAM=settings.mail_message_stream,
        HR_CC_EMAILS=settings.hr_cc_emails,
        FSI_OPS_EMAIL=settings.fsi_ops_email,
        STELLAR_SUPPORT_EMAIL=settings.stellar_support_email,
        STELLAR_SALES_EMAIL=settings.stellar_sales_email,
    )

    db.init_app(app)

    app.register_blueprint(intake_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(help_bp)
    app.register_blueprint(webhooks_bp)

    return app
