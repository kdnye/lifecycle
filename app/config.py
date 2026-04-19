import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_env: str
    fsi_production: bool
    secret_key: str | None
    database_url: str | None
    postmark_server_token: str | None
    default_sender_email: str
    mail_message_stream: str
    hr_cc_emails: str
    fsi_ops_email: str
    stellar_support_email: str
    stellar_sales_email: str


def load_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        fsi_production=os.getenv("FSI_PRODUCTION", "false").lower() == "true",
        secret_key=os.getenv("SECRET_KEY"),
        database_url=os.getenv("DATABASE_URL"),
        postmark_server_token=os.getenv("POSTMARK_SERVER_TOKEN"),
        default_sender_email=os.getenv("DEFAULT_SENDER_EMAIL", "it-automation@freightservices.net"),
        mail_message_stream=os.getenv("MAIL_MESSAGE_STREAM", "outbound"),
        hr_cc_emails=os.getenv(
            "HR_CC_EMAILS",
            "hr@freightservices.net, suzann.ghekas@freightservices.net",
        ),
        fsi_ops_email=os.getenv("FSI_OPS_EMAIL", "ops@freightservices.net"),
        stellar_support_email=os.getenv("STELLAR_SUPPORT_EMAIL", "support@stellar.tech"),
        stellar_sales_email=os.getenv("STELLAR_SALES_EMAIL", "sales@stellar.tech"),
    )


def validate_production_settings(settings: Settings) -> list[str]:
    issues: list[str] = []
    if settings.fsi_production:
        if not settings.secret_key:
            issues.append("Missing required SECRET_KEY while FSI_PRODUCTION=true.")
        if not settings.database_url:
            issues.append("Missing required DATABASE_URL while FSI_PRODUCTION=true.")
        if not settings.postmark_server_token:
            issues.append("Missing required POSTMARK_SERVER_TOKEN while FSI_PRODUCTION=true.")
    return issues
