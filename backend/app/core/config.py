"""Application configuration loaded from environment variables.

Uses pydantic-settings so every setting is validated and has a documented
default. Secrets are never hardcoded in code; they come from the environment.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object for the whole application.

    Values are read from environment variables and an optional ``.env`` file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Business Management Portal"
    APP_ENV: str = Field(default="development")
    APP_DEBUG: bool = Field(default=True)
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8000)
    API_V1_PREFIX: str = Field(default="/api/v1")

    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_JSON: bool = Field(default=False)

    # Security
    SECRET_KEY: str = Field(default="")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30)

    # Auth session cookies (refresh token)
    AUTH_COOKIE_NAME: str = Field(default="bmp_refresh")
    AUTH_COOKIE_SECURE: bool = Field(default=False)  # must be True in production (HTTPS)
    AUTH_COOKIE_SAMESITE: str = Field(default="lax")
    AUTH_COOKIE_DOMAIN: str = Field(default="")

    # Platform owner bootstrap (development only)
    BOOTSTRAP_PLATFORM_OWNER_EMAIL: str = Field(default="")
    BOOTSTRAP_PLATFORM_OWNER_PASSWORD: str = Field(default="")
    BOOTSTRAP_PLATFORM_OWNER_NAME: str = Field(default="")

    # Database
    DATABASE_URL: str = Field(default="postgresql+asyncpg://bmp_user:bmp_password@localhost:5432/bmp")
    POSTGRES_DB: str = Field(default="bmp")
    POSTGRES_USER: str = Field(default="bmp_user")
    POSTGRES_PASSWORD: str = Field(default="")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_PASSWORD: str = Field(default="")

    # MinIO
    MINIO_ENDPOINT: str = Field(default="localhost:9000")
    MINIO_PUBLIC_ENDPOINT: str = Field(default="localhost:9000")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin")
    MINIO_SECRET_KEY: str = Field(default="")
    MINIO_BUCKET: str = Field(default="bmp-documents")
    MINIO_SECURE: bool = Field(default=False)

    # CORS
    CORS_ORIGINS: str = Field(default="http://localhost:3000,http://frontend:3000")

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _split_cors_origins(cls, value: str) -> str:
        return ",".join(origin.strip() for origin in value.split(",") if origin.strip())

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list, ready for FastAPI middleware."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def sqlalchemy_sync_url(self) -> str:
        """Return a synchronous URL for tools that need a sync engine (e.g. Alembic)."""
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (loads .env once per process)."""
    return Settings()