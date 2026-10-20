import json
import re
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings with safe local defaults."""

    model_config = SettingsConfigDict(
        env_prefix="BACKEND_",
        env_file=(".env", "backend/.env"),
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "UNKNOWN FastAPI Backend"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=1, ge=1, le=8)
    database_url: str = "sqlite+aiosqlite:///./backend-dev.db"
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=200)
    db_pool_timeout: float = Field(default=30.0, gt=0, le=300)
    db_pool_recycle: int = Field(default=1800, ge=0, le=86400)
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    trusted_hosts: Annotated[list[str], NoDecode] = ["localhost", "127.0.0.1", "test"]
    request_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    log_level: str = "INFO"
    auth_secret: str = "development-only-change-this-secret"
    admin_username: str = Field(default="admin", min_length=1, max_length=120)
    admin_password: str = "change-me-in-development"
    admin_password_hash: str | None = None
    allow_dev_admin: bool = True

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        value = value.strip().lower()
        allowed = {"development", "test", "staging", "production"}
        if value not in allowed:
            raise ValueError(f"environment must be one of {sorted(allowed)}")
        return value

    @field_validator("cors_origins", "trusted_hosts", mode="before")
    @classmethod
    def parse_csv_values(cls, value: object) -> object:
        if isinstance(value, str):
            raw_value = value.strip()
            if raw_value.startswith("["):
                parsed = json.loads(raw_value)
                if not isinstance(parsed, list):
                    raise ValueError("list settings must be a JSON array or comma-separated values")
                return [str(item).strip() for item in parsed if str(item).strip()]
            return [item.strip() for item in raw_value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.environment == "production":
            if self.auth_secret == "development-only-change-this-secret":
                raise ValueError("BACKEND_AUTH_SECRET must be configured in production")
            if len(self.auth_secret) < 32:
                raise ValueError("BACKEND_AUTH_SECRET must be at least 32 characters in production")
            if self.admin_username.strip().lower() == "admin":
                raise ValueError("BACKEND_ADMIN_USERNAME must not use the default admin username in production")
            if not self.admin_password_hash:
                raise ValueError("BACKEND_ADMIN_PASSWORD_HASH must be configured in production")
            if not re.fullmatch(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}", self.admin_password_hash):
                raise ValueError("BACKEND_ADMIN_PASSWORD_HASH must be a valid bcrypt hash in production")
            if self.database_url.startswith("sqlite"):
                raise ValueError("BACKEND_DATABASE_URL must use the production database in production")
            if self.allow_dev_admin:
                raise ValueError("BACKEND_ALLOW_DEV_ADMIN must be false in production")
            if self.cors_origins == ["http://localhost:3000"]:
                raise ValueError("BACKEND_CORS_ORIGINS must be configured in production")
            if self.trusted_hosts == ["localhost", "127.0.0.1", "test"]:
                raise ValueError("BACKEND_TRUSTED_HOSTS must be configured in production")
            if "*" in self.cors_origins or "*" in self.trusted_hosts:
                raise ValueError("Wildcard CORS origins and trusted hosts are not allowed in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
