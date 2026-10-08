"""Refund rollback, concurrency and history checks in a disposable DB only."""

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4, uuid5

from sqlalchemy import func, select, text

from k_loto.application.admin import ADMIN_NAMESPACE
from k_loto.application.halloween_transition import HalloweenTransitionService
from k_loto.application.scheduler import DrawRecoveryService
from k_loto.application.weekly import LotteryTicketPurchaseService
from k_loto.core.config import get_settings
from k_loto.domain.enums import (
    LedgerAccountKind,
    TicketStatus,
    TransactionType,
)
from k_loto.infrastructure.database.models import (
    Balance,
    LedgerTransaction,
    Lottery,
    Ticket,
    User,
)
from k_loto.infrastructure.database.session import engine, session_factory


async def fingerprint() -> tuple[str, str, int, int]:
    async with session_factory() as session:
        result = await session.execute(
            text("""
            SELECT
              (SELECT md5(coalesce(string_agg(
                row_to_json(d)::text, '' ORDER BY id), ''))
               FROM draws d WHERE status='COMPLETED'),
              (SELECT md5(coalesce(string_agg(
                row_to_json(t)::text, '' ORDER BY id), ''))
               FROM tickets t WHERE status='SETTLED'),
              (SELECT count(*) FROM tickets),
              (SELECT count(*) FROM ledger_transactions)
        """)
        )
        row = result.one()
        return row[0], row[1], row[2], row[3]


async def main() -> None:
    settings = get_settings()
    if not str(settings.database_url).rstrip("/").endswith("/k_loto_halloween_smoke"):
        raise RuntimeError("Halloween smoke requires its disposable database.")
    if not settings.admin_username:
        raise RuntimeError("Configured admin audit identity is required.")
    owner_id = uuid5(ADMIN_NAMESPACE, settings.admin_username.casefold())
    await DrawRecoveryService(session_factory).reconcile()
    user_id = uuid4()
    async with session_factory() as session, session.begin():
        session.add(User(id=user_id, display_name="Halloween smoke", is_active=True))
        await session.flush()
        session.add(Balance(user_id=user_id, amount=50_000, version=1))
        session.add(
            LedgerTransaction(
                id=uuid4(),
                operation_id=uuid4(),
                idempotency_key=f"smoke:{user_id}",
                account_kind=LedgerAccountKind.USER_BALANCE,
                account_id=user_id,
                type=TransactionType.SYSTEM_ADJUSTMENT,
                amount=50_000,
                balance_before=0,
                balance_after=50_000,
                user_id=user_id,
                details={"reason": "Disposable Halloween PostgreSQL smoke"},
            )
        )
    async with session_factory() as session:
        purchase = await LotteryTicketPurchaseService(
            session, lottery_code="grob"
        ).purchase(
            user_id=user_id,
            combinations=[[1, 2, 3], [2, 3, 16]],
            idempotency_key=f"smoke:{user_id}:buy",
        )
    before = await fingerprint()
    # Force failure after all account/ticket changes; transaction must restore
    # data even if SQLAlchemy already autoflushed earlier parts of the operation.
    async with session_factory() as session:
        with patch.object(
            session, "flush", AsyncMock(side_effect=RuntimeError("smoke rollback"))
        ):
            try:
                await HalloweenTransitionService(session).activate(owner_id=owner_id)
            except RuntimeError as error:
                assert str(error) == "smoke rollback"
            else:
                raise AssertionError("Injected rollback did not happen.")
    assert await fingerprint() == before
    async with session_factory() as session:
        assert (
            await session.scalar(
                select(Balance.amount).where(Balance.user_id == user_id)
            )
            == 36_668
        )
        assert (
            await session.scalar(
                select(Lottery.ruleset_code).where(Lottery.code == "grob")
            )
            == "grob_3_16"
        )

    async def activate():
        async with session_factory() as session:
            return await HalloweenTransitionService(session).activate(owner_id=owner_id)

    results = await asyncio.gather(activate(), activate())
    assert sum(result.already_processed for result in results) == 1
    after = await fingerprint()
    assert after[:3] == before[:3]  # Completed draws, settled tickets, ticket count.
    async with session_factory() as session:
        assert (
            await session.scalar(
                select(Balance.amount).where(Balance.user_id == user_id)
            )
            == 50_000
        )
        assert (
            await session.scalar(
                select(func.count(Ticket.id)).where(
                    Ticket.id.in_(purchase.ticket_ids),
                    Ticket.status == TicketStatus.REFUNDED,
                )
            )
            == 2
        )
        total = await session.scalar(
            select(func.sum(LedgerTransaction.amount)).where(
                LedgerTransaction.idempotency_key.like("halloween-3-28:%")
            )
        )
        assert total == 0
    assert (await activate()).already_processed
    assert await fingerprint() == after
    # New purchases accept 28 and use the new draw snapshot immediately.
    async with session_factory() as session:
        fresh = await LotteryTicketPurchaseService(
            session, lottery_code="grob"
        ).purchase(
            user_id=user_id,
            combinations=[[1, 14, 28]],
            idempotency_key=f"smoke:{user_id}:new",
            now=datetime.now(UTC),
        )
        assert fresh.total_cost == 6666
    print(
        json.dumps(
            {
                "rollback": True,
                "concurrent_idempotency": True,
                "completed_history_unchanged": True,
                "balanced_refunds": True,
                "new_3_28_purchase": True,
            }
        )
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
