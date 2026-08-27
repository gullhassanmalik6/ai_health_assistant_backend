"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import Environment
from app.core.db_url import is_local_database_host, normalize_database_url, stripped_database_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
        populate_by_name=True,
    )

    APP_NAME: str = "AI Doctor API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://aidoctor:aidoctor@localhost:5432/aidoctor",
        validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_URL", "POSTGRESQL_URL"),
    )
    TEST_DATABASE_URL: str = (
        "postgresql+asyncpg://aidoctor:aidoctor@localhost:5432/aidoctor_test"
    )

    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_CLIENT_EMAIL: str = ""
    FIREBASE_PRIVATE_KEY: str = ""
    FIREBASE_API_KEY: str = ""
    FIREBASE_CREDENTIALS_PATH: str | None = None
    FIREBASE_CREDENTIALS_JSON: str | None = None

    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8080,http://127.0.0.1:8080,http://127.0.0.1:3000"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    AUTH_RATE_LIMIT_PER_MINUTE: int = 10

    REQUEST_TIMEOUT_SECONDS: float = 15.0

    @field_validator("DATABASE_URL", "TEST_DATABASE_URL")
    @classmethod
    def normalize_database_urls(cls, value: str) -> str:
        return stripped_database_url(normalize_database_url(value))

    @field_validator("FIREBASE_PRIVATE_KEY")
    @classmethod
    def normalize_private_key(cls, value: str) -> str:
        if not value:
            return value
        return value.replace("\\n", "\n")

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def is_test(self) -> bool:
        return self.ENVIRONMENT == Environment.TEST

    @property
    def cors_origins(self) -> list[str]:
        origins = [item.strip() for item in self.CORS_ALLOWED_ORIGINS.split(",") if item.strip()]
        if self.is_production and ("*" in origins or not origins):
            raise ValueError(
                "CORS_ALLOWED_ORIGINS must be an explicit origin list in production."
            )
        return origins

    @property
    def allowed_hosts_list(self) -> list[str]:
        hosts = [item.strip() for item in self.ALLOWED_HOSTS.split(",") if item.strip()]
        if self.is_production and ("*" in hosts or not hosts):
            raise ValueError("ALLOWED_HOSTS must be an explicit host list in production.")
        return hosts

    @property
    def use_trusted_host_middleware(self) -> bool:
        hosts = set(self.allowed_hosts_list)
        loopback_only = hosts <= {"localhost", "127.0.0.1", "::1"}
        if loopback_only:
            return False
        return bool(hosts) and "*" not in hosts

    def assert_database_configured(self) -> None:
        if self.is_production and is_local_database_host(self.DATABASE_URL):
            raise RuntimeError(
                "DATABASE_URL points at localhost. On Render/Railway/Fly you must attach a "
                "PostgreSQL instance and set DATABASE_URL to that host (not 127.0.0.1:5432). "
                "Use the provider URL; postgres:// is accepted and converted for asyncpg."
            )

    @property
    def alembic_sync_database_url(self) -> str:
        """Alembic env.py uses this when a sync driver is needed."""
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
