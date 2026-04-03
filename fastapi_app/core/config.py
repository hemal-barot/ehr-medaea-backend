import os
from functools import lru_cache
from typing import List


class Settings:
    app_name: str = "Medaea EHR API"
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"

    # ─── Database ──────────────────────────────────────────────────────────────
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    postgres_db: str = os.getenv("POSTGRES_DB", "medaea-v2")
    postgres_server: str = os.getenv("POSTGRES_SERVER", "localhost")
    postgres_port: str = os.getenv("POSTGRES_PORT", "5432")

    @property
    def database_url(self) -> str:
        # Prefer explicitly set DATABASE_URL (e.g. Replit managed DB)
        explicit = os.getenv("DATABASE_URL", "")
        if explicit:
            return explicit
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}"
        )

    # ─── JWT / Auth ────────────────────────────────────────────────────────────
    secret_key: str = os.getenv(
        "SECRET_KEY",
        "288a408a22913eb632da9a1b2ae254c5f3b9f6cc692323f8f1e6f6c7103a707c",
    )
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "11520"))

    # ─── Email ─────────────────────────────────────────────────────────────────
    require_email_verification: bool = os.getenv("REQUIRE_EMAIL_VERIFICATION", "false").lower() == "true"
    enable_activation_reminder: bool = os.getenv("ENABLE_ACTIVATION_REMINDER_JOB", "true").lower() == "true"
    activation_reminder_hour_utc: int = int(os.getenv("ACTIVATION_REMINDER_HOUR_UTC", "12"))

    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_starttls: bool = os.getenv("SMTP_STARTTLS", "true").lower() == "true"
    smtp_ssl_tls: bool = os.getenv("SMTP_SSL_TLS", "false").lower() == "true"
    emails_from_email: str = os.getenv("EMAILS_FROM_EMAIL", "noreply@medaea.com")
    emails_from_name: str = os.getenv("EMAILS_FROM_NAME", "Medaea EHR")
    use_credentials: bool = os.getenv("USE_CREDENTIALS", "true").lower() == "true"
    validate_certs: bool = os.getenv("VALIDATE_CERTS", "true").lower() == "true"
    email_file_path: str = os.getenv("EMAIL_FILE_PATH", "./emails")

    # ─── Frontend ──────────────────────────────────────────────────────────────
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    @property
    def allowed_origins(self) -> List[str]:
        import json
        raw = os.getenv("BACKEND_CORS_ORIGINS", "")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return [o.strip() for o in raw.split(",")]
        return ["http://localhost:5173", "http://localhost:3000", "http://localhost:5000"]

    # ─── MFA ───────────────────────────────────────────────────────────────────
    mfa_encryption_key: str = os.getenv(
        "MFA_ENCRYPTION_KEY",
        "b7-PqUqy4_k2zPUHRpsL2PUWmXglTjdBpOZibh6CT7Q=",
    )
    mfa_token_expire_minutes: int = int(os.getenv("MFA_TOKEN_EXPIRE_MINUTES", "5"))

    # ─── Twilio ────────────────────────────────────────────────────────────────
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_phone_number: str = os.getenv("TWILIO_PHONE_NUMBER", "")

    # ─── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ─── Storage ───────────────────────────────────────────────────────────────
    use_s3: bool = os.getenv("USE_S3", "false").lower() == "true"
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")

    # ─── Migrations ────────────────────────────────────────────────────────────
    run_migrations_on_startup: bool = os.getenv("RUN_MIGRATIONS_ON_STARTUP", "true").lower() == "true"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
