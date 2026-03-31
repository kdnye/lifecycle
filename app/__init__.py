from flask import Flask

from app.config import load_settings, validate_production_settings
from app.models import db
from app.routes.health import health_bp
from app.routes.intake import intake_bp


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates")

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
    )

    db.init_app(app)

    app.register_blueprint(intake_bp)
    app.register_blueprint(health_bp)

    return app
