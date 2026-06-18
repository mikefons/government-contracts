"""Application settings, loaded from environment / .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    database_url: str = "sqlite:///./chancery.db"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    # Auth
    secret_key: str = "CHANGE_ME_dev_only_secret_do_not_use_in_prod"
    access_token_expire_minutes: int = 720
    jwt_algorithm: str = "HS256"

    # Bootstrap admin (created on first boot if no users exist)
    admin_email: str = "admin@chancery.local"
    admin_password: str = "changeme"

    # Schema management
    run_create_all: bool = True   # dev convenience; use Alembic in prod

    # Serverless (Vercel) mode: no background scheduler, no in-memory rate limiter,
    # no DB connection pooling held across invocations.
    serverless: bool = False
    enable_rate_limit: bool = True

    # Rate limiting (per client IP)
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    # Scheduled ingest
    enable_scheduler: bool = False
    ingest_interval_minutes: int = 360

    # Agent providers
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"
    ollama_host: str | None = None
    ollama_model: str = "llama3.1"

    # Intelligence graph backend
    graph_backend: str = "memory"   # memory | arango
    arango_url: str = "http://localhost:8529"
    arango_db: str = "chancery"
    arango_user: str = "root"
    arango_password: str = ""

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
