import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_env: str
    fsi_production: bool
    secret_key: str | None
    database_url: str | None
    postmark_server_token: str | None
    mail_default_sender: str | None
    mail_message_stream: str


def load_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        fsi_production=os.getenv("FSI_PRODUCTION", "false").lower() == "true",
        secret_key=os.getenv("SECRET_KEY"),
        database_url=os.getenv("DATABASE_URL"),
        postmark_server_token=os.getenv("POSTMARK_SERVER_TOKEN"),
        mail_default_sender=os.getenv("MAIL_DEFAULT_SENDER"),
        mail_message_stream=os.getenv("MAIL_MESSAGE_STREAM", "onboarding"),
    )


def validate_production_settings(settings: Settings) -> list[str]:
    issues: list[str] = []
    if settings.fsi_production:
        if not settings.secret_key:
            issues.append("Missing required SECRET_KEY while FSI_PRODUCTION=true.")
        if not settings.database_url:
            issues.append("Missing required DATABASE_URL while FSI_PRODUCTION=true.")
    return issues
