"""Alembic migration environment."""

import asyncio
from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from k_loto.core.config import get_settings
from k_loto.infrastructure.database import models  # noqa: F401
from k_loto.infrastructure.database.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", str(get_settings().database_url))
target_metadata = Base.metadata

_ENUM_CHECK_CONSTRAINTS = {
    "ck_admin_audit_log_audit_action",
    "ck_draws_draw_status",
    "ck_ledger_transactions_ledger_account_kind",
    "ck_ledger_transactions_transaction_type",
    "ck_lotteries_lottery_kind",
    "ck_notification_outbox_notification_status",
    "ck_notification_outbox_notification_type",
    "ck_tickets_ticket_status",
}


def include_object(
    _object: Any,
    name: str | None,
    type_: str,
    _reflected: bool,
    _compare_to: Any,
) -> bool:
    """Ignore SQLAlchemy Enum checks that the check-constraint plugin misdiffs."""
    return not (type_ == "check_constraint" and name in _ENUM_CHECK_CONSTRAINTS)


def run_migrations_offline() -> None:
    """Run migrations without a live database connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure and execute migrations on a synchronous connection proxy."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations through Alembic."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations with a database connection."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
