from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"
    database_url: str = "sqlite:///./dev.db"
    redis_url: str = ""
    jwt_secret: str = "dev-only-secret-change-me"
    jwt_expire_minutes: int = 1440
    frontend_origins: str = "http://localhost:3000"

    google_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    rapidapi_key: str = ""

    wikipedia_enabled: bool = True
    auto_migrate: bool = True  # run Alembic migrations on startup (single-instance deploys)
    company_cache_ttl_seconds: int = 21600  # 6 h: opening counts go stale
    max_alerts_per_user: int = 5

    # Week 4: alert emails (any SMTP provider: Brevo, Gmail app password, ...). Empty host = in-app only.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""
    public_app_url: str = "http://localhost:3000"   # links in emails
    public_api_url: str = "http://localhost:8000"   # unsubscribe link
    cron_token: str = ""  # shared secret for POST /internal/alerts/dispatch; empty disables the endpoint

    sentry_dsn: str = ""
    admin_emails: str = ""  # comma-separated; can view /stats
    rate_limit_per_minute: int = 30
    search_cache_ttl_seconds: int = 900

    @property
    def sqlalchemy_url(self) -> str:
        """Hosted Postgres providers hand out postgres:// URLs; SQLAlchemy needs the psycopg driver name."""
        url = self.database_url
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.env == "production" and s.jwt_secret.startswith("dev-only"):
        raise RuntimeError("JWT_SECRET must be set in production")
    return s
