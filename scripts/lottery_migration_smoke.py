"""Verify the two lottery additions on an isolated production restore."""

import asyncio
import hashlib
import subprocess
import sys

from sqlalchemy import text

from k_loto.core.config import get_settings
from k_loto.infrastructure.database.session import engine, session_factory
from scripts import achievement_migration_smoke as history

IDS = "'10000000-0000-0000-0000-000000001066','10000000-0000-0000-0000-000000001067'"
history.QUERIES["ledger"] = (
    "SELECT * FROM ledger_transactions WHERE lottery_id IS NULL "
    f"OR lottery_id NOT IN ({IDS}) ORDER BY id"
)
history.QUERIES["jackpots"] = (
    f"SELECT * FROM jackpot_accounts WHERE lottery_id NOT IN ({IDS}) ORDER BY id"
)


async def fingerprints():
    """Hash all rows on PostgreSQL; return bounded digests rather than raw history."""
    result = {}
    async with session_factory() as session:
        for key, query in history.QUERIES.items():
            # Row identity is included in JSON. Sorting hashes inside 256 buckets
            # preserves multiplicity without random primary-key scans or sending
            # the entire financial archive through Python three times.
            source = query.rsplit(" ORDER BY ", 1)[0]
            rows = await session.execute(
                text(
                    "SELECT left(h,2),count(*),md5(string_agg(h,'' ORDER BY h)) "
                    "FROM (SELECT md5(row_to_json(s)::text) h FROM ("
                    + source
                    + ") s) hashed GROUP BY left(h,2) ORDER BY left(h,2)"
                )
            )
            digest = hashlib.sha256()
            for row in rows:
                digest.update(repr(tuple(row)).encode())
            result[key] = digest.hexdigest()
    return result


history.fingerprints = fingerprints


async def verify(before, runtime):
    assert await history.fingerprints() == before, "Existing financial history changed"
    assert await history.runtime_state() == runtime, "Achievement runtime changed"
    async with session_factory() as session:
        rows = (
            await session.execute(
                text("""
            SELECT l.code,l.numbers_to_pick,l.max_number,l.ticket_price,
                   l.max_tickets_per_purchase,l.max_tickets_per_user_per_draw,
                   j.balance,j.base_amount,l.timezone,l.sales_cutoff_minutes
            FROM lotteries l JOIN jackpot_accounts j ON j.lottery_id=l.id
            WHERE l.code IN ('mini','newyear2027') ORDER BY l.code
        """)
            )
        ).all()
        assert [tuple(r) for r in rows] == [
            ("mini", 6, 30, 10000, 100, 500, 20000000, 20000000, "Europe/Moscow", 2),
            ("newyear2027", 3, 12, 10000, 101, 101, 0, 0, "Europe/Moscow", 2),
        ], rows
        amount = await session.scalar(
            text(
                "SELECT coalesce(sum(amount),0) FROM ledger_transactions "
                f"WHERE lottery_id IN ({IDS})"
            )
        )
        assert amount == 20000000, amount
    await engine.dispose()


def main():
    if get_settings().app_env != "test" or not (engine.url.database or "").startswith(
        "k_loto_achievement_restore_"
    ):
        raise RuntimeError("Disposable production restore only")
    before, runtime = asyncio.run(history.baseline())
    for _ in range(2):
        subprocess.run([sys.executable, "-m", "scripts.migrate_database"], check=True)
        asyncio.run(verify(before, runtime))
    print(
        "Lottery migrations: history/runtime preserved; "
        "new accounts exact; repeat idempotent"
    )


if __name__ == "__main__":
    main()
