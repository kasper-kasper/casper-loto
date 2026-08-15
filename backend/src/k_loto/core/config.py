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
    miniapp_dev_auth_enabled: bool = False
    miniapp_dev_session_secret: SecretStr | None = None
    miniapp_dev_session_max_age_seconds: int = Field(default=28800, ge=300, le=86400)
    miniapp_dev_user_telegram_id: int = Field(default=900000001, gt=0)
    miniapp_dev_initial_balance: int = Field(default=100_000, ge=0)
    miniapp_dev_weekly_ticket_price: int = Field(default=100, gt=0)
    miniapp_dev_weekly_base_jackpot: int = Field(default=10_000, ge=0)
    miniapp_dev_weekly_reserve: int = Field(default=100_000, ge=0)
    admin_secret: SecretStr | None = None
    admin_username: str | None = None
    admin_password_hash: SecretStr | None = None
    admin_session_max_age_seconds: int = Field(default=28_800, ge=300, le=86_400)

    @property
    def docs_enabled(self) -> bool:
        """Keep interactive docs off by default in production."""
        return self.app_env != "production"

    @property
    def local_dev_auth_available(self) -> bool:
        """Never permit browser bypass outside an explicit development runtime."""
        return (
            self.app_env == "development"
            and self.miniapp_dev_auth_enabled
            and self.miniapp_dev_session_secret is not None
            and len(self.miniapp_dev_session_secret.get_secret_value()) >= 32
        )

    @property
    def admin_auth_available(self) -> bool:
        """Require a complete credential set before exposing administrator login."""
        return (
            self.admin_secret is not None
            and len(self.admin_secret.get_secret_value()) >= 32
            and self.admin_username is not None
            and bool(self.admin_username.strip())
            and self.admin_password_hash is not None
        )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings object."""
    return Settings()
