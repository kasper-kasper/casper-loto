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
    owner_telegram_id: int | None = Field(default=None, gt=0)
    owner_daily_summary_enabled: bool = True
    operational_stuck_minutes: int = Field(default=10, ge=5, le=1440)
    monitoring_backup_dir: str = "/backups"
    lottery_bot_token: SecretStr | None = None
    publication_channel: str | None = Field(default=None, max_length=100)
    bot_outbox_interval_seconds: int = Field(default=2, ge=1, le=60)
    bot_max_tickets_per_purchase: int = Field(default=50, ge=1, le=100)
    miniapp_purchase_requests_per_minute: int = Field(default=10, ge=1, le=120)
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
    admin_remember_max_age_seconds: int = Field(
        default=7_776_000, ge=86_400, le=31_536_000
    )
    web_enabled: bool = True
    web_session_secret: SecretStr | None = None
    web_session_max_age_seconds: int = Field(default=604_800, ge=300, le=2_592_000)

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

    @property
    def web_auth_available(self) -> bool:
        """Enable ordinary browser accounts only with an independent strong secret."""
        return (
            self.web_enabled
            and self.web_session_secret is not None
            and len(self.web_session_secret.get_secret_value()) >= 32
        )


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings object."""
    return Settings()
