import os
from dataclasses import dataclass
from urllib.parse import quote_plus

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


@dataclass(frozen=True)
class Settings:
    app_env: str
    fsi_production: bool
    secret_key: str | None
    database_url: str | None
    postmark_server_token: str | None
    postmark_webhook_token: str | None
    default_sender_email: str
    mail_message_stream: str
    postmark_onboarding_message_stream: str
    hr_cc_emails: str
    fsi_ops_email: str
    stellar_support_email: str
    stellar_sales_email: str
    internal_cron_shared_secret: str | None
    asset_photos_bucket: str | None
    mail_suppress_send: bool
    pool_recycle: int
    pool_max_overflow: int


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _build_database_url_from_components() -> str | None:
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASS")
    db_name = os.getenv("DB_NAME")
    instance_connection_name = os.getenv("INSTANCE_CONNECTION_NAME")
    if not all([db_user, db_pass, db_name, instance_connection_name]):
        return None

    user = quote_plus(db_user)
    password = quote_plus(db_pass)
    database = quote_plus(db_name)
    instance = instance_connection_name.strip()

    return (
        "postgresql+pg8000://"
        f"{user}:{password}@/{database}"
        f"?unix_sock=/cloudsql/{instance}/.s.PGSQL.5432"
    )


def _resolve_database_url() -> str | None:
    # Prefer Cloud SQL component-based configuration when present (Cloud Run),
    # then fall back to DATABASE_URL (local/dev or explicit override).
    return _build_database_url_from_components() or os.getenv("DATABASE_URL")


def _resolve_production_flag() -> bool:
    explicit_flag = os.getenv("FSI_PRODUCTION")
    if explicit_flag is not None:
        return _is_truthy(explicit_flag)

    # Cloud Run always provides K_SERVICE; treat that as production unless explicitly overridden.
    return bool(os.getenv("K_SERVICE"))


def load_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        fsi_production=_resolve_production_flag(),
        secret_key=os.getenv("SECRET_KEY"),
        database_url=_resolve_database_url(),
        postmark_server_token=os.getenv("POSTMARK_SERVER_TOKEN"),
        postmark_webhook_token=os.getenv("POSTMARK_WEBHOOK_TOKEN"),
        default_sender_email=os.getenv("DEFAULT_SENDER_EMAIL", "it-automation@freightservices.net"),
        mail_message_stream=os.getenv("MAIL_MESSAGE_STREAM", "outbound"),
        postmark_onboarding_message_stream=os.getenv(
            "POSTMARK_ONBOARDING_MESSAGE_STREAM",
            os.getenv("MAIL_MESSAGE_STREAM", "outbound"),
        ),
        hr_cc_emails=os.getenv(
            "HR_CC_EMAILS",
            "hr@freightservices.net, suzann.ghekas@freightservices.net",
        ),
        fsi_ops_email=os.getenv("FSI_OPS_EMAIL", "ops@freightservices.net"),
        stellar_support_email=os.getenv("STELLAR_SUPPORT_EMAIL", "support@stellar.tech"),
        stellar_sales_email=os.getenv("STELLAR_SALES_EMAIL", "sales@stellar.tech"),
        internal_cron_shared_secret=os.getenv("INTERNAL_CRON_SHARED_SECRET"),
        asset_photos_bucket=os.getenv("ASSET_PHOTOS_BUCKET"),
        mail_suppress_send=_is_truthy(os.getenv("MAIL_SUPPRESS_SEND", "false")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
        pool_max_overflow=int(os.getenv("DB_POOL_MAX_OVERFLOW", "5")),
    )


def validate_production_settings(settings: Settings) -> list[str]:
    issues: list[str] = []
    if settings.fsi_production:
        if not settings.secret_key:
            issues.append("Missing required SECRET_KEY while FSI_PRODUCTION=true.")
        if not (settings.postmark_server_token or "").strip():
            issues.append(
                "Missing required POSTMARK_SERVER_TOKEN while FSI_PRODUCTION=true. "
                "Set this to the Postmark Server API token used for transactional email."
            )
        if not settings.database_url:
            issues.append("Missing required DATABASE_URL while FSI_PRODUCTION=true.")
        elif not settings.database_url.startswith(("postgresql://", "postgresql+")):
            issues.append(
                "DATABASE_URL must be PostgreSQL in production (expected postgresql:// or postgresql+driver://)."
            )
        else:
            try:
                make_url(settings.database_url)
            except (ArgumentError, ValueError):
                issues.append("DATABASE_URL is malformed and could not be parsed by SQLAlchemy.")
    return issues
