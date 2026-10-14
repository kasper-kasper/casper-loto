"""Upgrade an existing database, or seed the prerequisites of an empty one."""

import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID, uuid5

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from k_loto.infrastructure.database.session import engine, session_factory

ROOT = Path(__file__).resolve().parents[1]
FOUNDATION = "0001_domain_model"
NAMESPACE = UUID("75af08de-485a-481a-bcc0-c7f0cb4588da")


async def revision() -> str | None:
    async with session_factory() as session:
        if not await session.scalar(
            text("SELECT to_regclass('public.alembic_version')")
        ):
            tables = await session.scalar(
                text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
            )
            if tables:
                raise RuntimeError(
                    "Unversioned nonempty schema requires manual migration review."
                )
            return None
        return await session.scalar(text("SELECT version_num FROM alembic_version"))


async def seed_foundation() -> None:
    async with session_factory() as session, session.begin():
        # Only the historical empty-schema prerequisites are supplied. Current
        # accounts, purchased tickets and completed business history are untouched.
        await session.execute(
            text("SELECT version_num FROM alembic_version FOR UPDATE")
        )
        for table in (
            "users",
            "draws",
            "tickets",
            "ledger_transactions",
            "admin_audit_log",
        ):
            if await session.scalar(text(f"SELECT count(*) FROM {table}")):
                raise RuntimeError(
                    "Foundation bootstrap refuses existing business history."
                )
        for code, kind, pick, maximum, schedule in (
            ("weekly", "WEEKLY", 5, 20, {"weekday": "sunday", "draw_time": "20:00"}),
            ("daily", "DAILY", 4, 15, {"slots": ["02:22", "12:00", "18:00"]}),
        ):
            identifier = uuid5(NAMESPACE, code)
            existing = await session.scalar(
                text("SELECT id FROM lotteries WHERE code=:code"), {"code": code}
            )
            if existing is not None:
                identifier = existing
            else:
                await session.execute(
                    text("""
                    INSERT INTO lotteries (id,code,name,kind,numbers_to_pick,max_number,
                        ticket_price,timezone,schedule,sales_cutoff_minutes,is_active)
                    VALUES (:id,:code,:name,:kind,:pick,:maximum,NULL,'Europe/Moscow',
                        CAST(:schedule AS jsonb),2,false)
                """),
                    {
                        "id": identifier,
                        "code": code,
                        "name": f"Legacy {code}",
                        "kind": kind,
                        "pick": pick,
                        "maximum": maximum,
                        "schedule": json.dumps(schedule),
                    },
                )
            for table in ("jackpot_accounts", "distribution_funds", "lottery_reserves"):
                extra_column = ",base_amount" if table == "jackpot_accounts" else ""
                extra_value = ",0" if extra_column else ""
                await session.execute(
                    text(f"""
                    INSERT INTO {table} (id,lottery_id,balance,version{extra_column})
                    SELECT :id,:lottery,0,1{extra_value}
                    WHERE NOT EXISTS (SELECT 1 FROM {table} WHERE lottery_id=:lottery)
                """),
                    {"id": uuid5(NAMESPACE, f"{code}:{table}"), "lottery": identifier},
                )
                if await session.scalar(
                    text(f"SELECT balance FROM {table} WHERE lottery_id=:id"),
                    {"id": identifier},
                ):
                    raise RuntimeError(
                        "Foundation bootstrap refuses a nonzero account."
                    )


async def isolated_loop(operation):
    try:
        return await operation()
    finally:
        await engine.dispose()


def migrate(target: str = "head") -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend/migrations"))
    current = asyncio.run(isolated_loop(revision))
    if current is None:
        command.upgrade(config, FOUNDATION)
        current = FOUNDATION
    if current == FOUNDATION:
        asyncio.run(isolated_loop(seed_foundation))
    command.upgrade(config, target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="head")
    options = parser.parse_args()
    migrate(options.target)
