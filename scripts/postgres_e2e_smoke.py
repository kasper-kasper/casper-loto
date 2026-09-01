"""One-off PostgreSQL smoke: 50 dashboards, concurrent buys, 5,000-ticket draw."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from time import perf_counter
from uuid import UUID, uuid4

from sqlalchemy import func, select

from k_loto.application.miniapp import MiniAppQueryService
from k_loto.application.weekly import (
    LotterySettlementService,
    LotteryTicketPurchaseService,
)
from k_loto.domain.enums import (
    DrawStatus,
    LedgerAccountKind,
    LotteryKind,
    TicketStatus,
    TransactionType,
)
from k_loto.infrastructure.database.models import (
    Balance,
    DistributionFund,
    Draw,
    JackpotAccount,
    LedgerTransaction,
    Lottery,
    LotteryReserve,
    Ticket,
    User,
)
from k_loto.infrastructure.database.session import session_factory


class FixedDailyNumbers:
    def draw(self, population_size: int, numbers_to_pick: int) -> tuple[int, ...]:
        assert (population_size, numbers_to_pick) == (15, 4)
        return (1, 2, 3, 4)


def ledger_credit(
    *,
    account_kind: LedgerAccountKind,
    account_id: UUID,
    amount: int,
    user_id: UUID | None = None,
    lottery_id: UUID | None = None,
) -> LedgerTransaction:
    return LedgerTransaction(
        id=uuid4(),
        operation_id=uuid4(),
        idempotency_key=f"smoke:seed:{account_kind.value}:{account_id}",
        account_kind=account_kind,
        account_id=account_id,
        type=TransactionType.SYSTEM_ADJUSTMENT,
        amount=amount,
        balance_before=0,
        balance_after=amount,
        user_id=user_id,
        lottery_id=lottery_id,
        details={"reason": "isolated PostgreSQL smoke"},
    )


async def seed() -> tuple[UUID, list[UUID], datetime]:
    now = datetime.now(UTC)
    lottery_id, draw_id = uuid4(), uuid4()
    user_ids = [uuid4() for _ in range(50)]
    async with session_factory() as session, session.begin():
        lottery = Lottery(
            id=lottery_id,
            code="smoke-daily",
            name="Smoke Daily",
            kind=LotteryKind.DAILY,
            ruleset_code="daily_4_15",
            numbers_to_pick=4,
            max_number=15,
            ticket_price=100,
            timezone="Europe/Moscow",
            schedule={"draw_time": "18:00"},
            sales_cutoff_minutes=2,
            max_tickets_per_purchase=1000,
            max_tickets_per_user_per_draw=5000,
            is_active=True,
            next_draw_number=2,
            next_ticket_number=1,
        )
        draw = Draw(
            id=draw_id,
            lottery_id=lottery_id,
            public_number=1,
            status=DrawStatus.SCHEDULED,
            scheduled_at=now + timedelta(minutes=5),
            sales_close_at=now + timedelta(minutes=4),
            correlation_id=uuid4(),
            ticket_count=0,
            total_sales=0,
            total_payout=0,
            reserve_used=0,
        )
        jackpot = JackpotAccount(
            id=uuid4(),
            lottery_id=lottery_id,
            balance=24_000_000,
            base_amount=24_000_000,
            version=1,
        )
        distribution = DistributionFund(
            id=uuid4(), lottery_id=lottery_id, balance=1_000_000_000, version=1
        )
        reserve = LotteryReserve(
            id=uuid4(), lottery_id=lottery_id, balance=1_000_000_000, version=1
        )
        session.add_all([lottery, draw, jackpot, distribution, reserve])
        session.add_all(
            [
                ledger_credit(
                    account_kind=LedgerAccountKind.JACKPOT,
                    account_id=jackpot.id,
                    amount=jackpot.balance,
                    lottery_id=lottery_id,
                ),
                ledger_credit(
                    account_kind=LedgerAccountKind.DISTRIBUTION_FUND,
                    account_id=distribution.id,
                    amount=distribution.balance,
                    lottery_id=lottery_id,
                ),
                ledger_credit(
                    account_kind=LedgerAccountKind.LOTTERY_RESERVE,
                    account_id=reserve.id,
                    amount=reserve.balance,
                    lottery_id=lottery_id,
                ),
            ]
        )
        for index, user_id in enumerate(user_ids):
            user = User(
                id=user_id,
                telegram_id=-(index + 1),
                display_name=f"Smoke {index + 1}",
                is_active=True,
                is_admin=False,
            )
            balance = Balance(user_id=user_id, amount=10_000_000, version=1)
            session.add_all(
                [
                    user,
                    balance,
                    ledger_credit(
                        account_kind=LedgerAccountKind.USER_BALANCE,
                        account_id=user_id,
                        amount=balance.amount,
                        user_id=user_id,
                    ),
                ]
            )
    return draw_id, user_ids, now


async def open_dashboard(user_id: UUID) -> None:
    async with session_factory() as session:
        result = await MiniAppQueryService(session).dashboard(user_id)
        assert result.lotteries and result.balance == 10_000_000


async def buy(user_id: UUID, count: int, key: str, now: datetime) -> None:
    combinations: list[list[int] | tuple[int, ...]] = [
        [1, 2, 3, 5] for _ in range(count)
    ]
    async with session_factory() as session:
        result = await LotteryTicketPurchaseService(
            session, lottery_code="smoke-daily"
        ).purchase(
            user_id=user_id, combinations=combinations, idempotency_key=key, now=now
        )
        assert len(result.ticket_ids) == count


async def main() -> None:
    draw_id, users, now = await seed()
    started = perf_counter()
    await asyncio.gather(*(open_dashboard(user_id) for user_id in users))
    dashboard_seconds = perf_counter() - started
    started = perf_counter()
    await asyncio.gather(
        *(
            buy(user_id, 10, f"concurrent-{index}", now)
            for index, user_id in enumerate(users[:5])
        )
    )
    for index, count in enumerate((1000, 1000, 1000, 1000, 950)):
        await buy(users[0], count, f"bulk-{index}", now)
    purchase_seconds = perf_counter() - started
    async with session_factory() as session:
        count = int(
            await session.scalar(
                select(func.count(Ticket.id)).where(Ticket.draw_id == draw_id)
            )
            or 0
        )
        assert count == 5_000
    started = perf_counter()
    async with session_factory() as session:
        result = await LotterySettlementService(session, FixedDailyNumbers()).settle(
            draw_id, now=now + timedelta(minutes=6)
        )
        assert not result.already_completed
    settlement_seconds = perf_counter() - started
    async with session_factory() as session:
        settled = int(
            await session.scalar(
                select(func.count(Ticket.id)).where(
                    Ticket.draw_id == draw_id, Ticket.status == TicketStatus.SETTLED
                )
            )
            or 0
        )
        assert settled == 5_000
    print(
        "postgres_smoke=passed dashboards=50 tickets=5000 "
        f"dashboard_seconds={dashboard_seconds:.3f} "
        f"purchase_seconds={purchase_seconds:.3f} "
        f"settlement_seconds={settlement_seconds:.3f}"
    )


if __name__ == "__main__":
    asyncio.run(main())
