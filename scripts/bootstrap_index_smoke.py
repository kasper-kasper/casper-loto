"""Exercise partial and invalid concurrent-index recovery on an empty audit DB."""

import asyncio
import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from k_loto.infrastructure.database.session import engine

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "backend/migrations/versions/0052_read_path_indexes.py"
)


async def main():
    if not str(engine.url.database).startswith("k_loto_bootstrap_smoke_"):
        raise RuntimeError("Disposable bootstrap database required")
    spec = importlib.util.spec_from_file_location(
        "index_recovery_fixture", MIGRATION_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    async with engine.connect() as connection:
        await connection.execution_options(isolation_level="AUTOCOMMIT")
        await connection.execute(
            text(
                "CREATE INDEX CONCURRENTLY ix_ticket_user_draw_status "
                "ON tickets (user_id,draw_id,status)"
            )
        )

    def upgrade(connection):
        context = MigrationContext.configure(connection)
        module.op = Operations(context)
        with context.begin_transaction():
            module.upgrade()

    async with engine.connect() as connection:
        await connection.run_sync(upgrade)
    # A failed CREATE INDEX CONCURRENTLY leaves the same owned definition with
    # indisvalid=false. This catalog fixture is restricted to the disposable DB.
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE pg_index SET indisvalid=false "
                "WHERE indexrelid='public.ix_ticket_user_draw_status'::regclass"
            )
        )
    async with engine.connect() as connection:
        await connection.run_sync(upgrade)
    async with engine.connect() as connection:
        invalid = await connection.scalar(
            text("SELECT count(*) FROM pg_index WHERE NOT indisvalid")
        )
        assert invalid == 0
    await engine.dispose()
    print("Fresh schema: partial and invalid concurrent-index recovery PASS")


if __name__ == "__main__":
    asyncio.run(main())
