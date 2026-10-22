"""Verify achievement migrations/catalog on a full disposable production restore."""

import asyncio
import hashlib
import subprocess
import sys
from typing import Any

from sqlalchemy import func, select, text

from k_loto.application.achievement_catalog import CatalogEntry, _import_catalog
from k_loto.application.achievement_release import approved_catalog
from k_loto.core.config import get_settings
from k_loto.infrastructure.database.achievement_models import (
    AchievementAward,
    AchievementDefinition,
    AchievementRuntime,
    CollectionUnlock,
)
from k_loto.infrastructure.database.session import engine, session_factory

QUERIES = {
    "balances": "SELECT user_id,amount FROM balances ORDER BY user_id",
    "ledger": "SELECT * FROM ledger_transactions ORDER BY id",
    "tickets": (
        "SELECT id,user_id,draw_id,status,purchase_price,prize_amount,numbers,source "
        "FROM tickets ORDER BY id"
    ),
    "draws": (
        "SELECT id,status,winning_numbers,configuration_snapshot FROM draws ORDER BY id"
    ),
    "fund": "SELECT * FROM kasper_fund_accounts ORDER BY id",
    "jackpots": "SELECT * FROM jackpot_accounts ORDER BY id",
}


async def fingerprints() -> dict[str, str]:
    # Stream small batches rather than aggregating all history in database RAM.
    result = {}
    async with session_factory() as session:
        for key, query in QUERIES.items():
            digest = hashlib.sha256()
            rows = await session.stream(
                text("SELECT row_to_json(s)::text FROM (" + query + ") s"),
                execution_options={"yield_per": 1000},
            )
            async for row in rows:
                digest.update(row[0].encode())
                digest.update(b"\n")
            result[key] = digest.hexdigest()
    return result


async def runtime_state() -> dict[str, Any] | None:
    async with session_factory() as session:
        if await session.scalar(
            text("SELECT to_regclass('public.achievement_runtime')")
        ):
            return await session.scalar(
                text("SELECT to_jsonb(r) FROM achievement_runtime r WHERE id=1")
            )
    return None


async def baseline() -> tuple[dict[str, str], dict[str, Any] | None]:
    values, state = await fingerprints(), await runtime_state()
    # Dispose on this same loop before the subprocess migration and next loop.
    await engine.dispose()
    return values, state


async def verify(before: dict[str, str], before_state: dict[str, Any] | None) -> None:
    async with session_factory() as session, session.begin():
        runtime = await session.get(AchievementRuntime, 1)
        assert runtime is not None
        entries = approved_catalog()
        definitions = list(await session.scalars(select(AchievementDefinition)))
        if before_state is None:
            assert not runtime.enabled and runtime.started_at is None
            assert runtime.scheduled_at is None and not definitions
            assert (
                await session.scalar(select(func.count()).select_from(AchievementAward))
                == 0
            )
            assert (
                await session.scalar(select(func.count()).select_from(CollectionUnlock))
                == 0
            )
            await _import_catalog(session, entries)
        else:
            actual = {
                d.code: CatalogEntry.model_validate(
                    {key: getattr(d, key) for key in CatalogEntry.model_fields}
                ).model_dump()
                for d in definitions
            }
            assert actual == {e.code: e.model_dump() for e in entries}
    if before_state is not None:
        assert await runtime_state() == before_state, (
            "Existing launch/schedule state changed"
        )
    assert await fingerprints() == before, "Migration/catalog altered business history"
    await engine.dispose()


if __name__ == "__main__":
    if get_settings().app_env != "test" or not (engine.url.database or "").startswith(
        "k_loto_achievement_restore_"
    ):
        raise RuntimeError("Only an explicit disposable production restore is allowed")
    values, state = asyncio.run(baseline())
    subprocess.run([sys.executable, "-m", "scripts.migrate_database"], check=True)
    subprocess.run([sys.executable, "-m", "alembic", "check"], check=True)
    asyncio.run(verify(values, state))
    print(
        "Full production restore: migrations, 93 definitions, launch state "
        "and financial/history fingerprints unchanged"
    )
