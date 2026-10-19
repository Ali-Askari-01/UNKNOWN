from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    database_url: str = "sqlite+aiosqlite:///./backend-dev.db"
    cors_origins: list[str] = ["http://localhost:3000"]
    trusted_hosts: list[str] = ["localhost", "127.0.0.1"]
    request_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    auth_secret: str = "development-only-change-this-secret"
    admin_username: str = "admin"
    admin_password: str = "change-me-in-development"
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
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
