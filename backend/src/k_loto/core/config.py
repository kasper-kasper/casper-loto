"""Typed application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings; secrets are supplied through the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_ignore_empty=True,
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"
    database_url: PostgresDsn
    scheduler_enabled: bool = True
    scheduler_interval_seconds: int = Field(default=30, ge=5, le=3600)
    lottery_bot_token: SecretStr | None = None
    bot_outbox_interval_seconds: int = Field(default=2, ge=1, le=60)
    telegram_init_data_max_age_seconds: int = Field(default=3600, ge=60, le=86400)
    miniapp_url: HttpUrl | None = None

    @property
    def docs_enabled(self) -> bool:
        """Keep interactive docs off by default in production."""
        return self.app_env != "production"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings object."""
    return Settings()
