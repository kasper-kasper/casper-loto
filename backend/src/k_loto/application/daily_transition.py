"""Safe completion of the one-time shared-Daily to PLL transition."""

from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.domain.enums import (
    LedgerAccountKind,
    TicketStatus,
    TransactionType,
)
from k_loto.infrastructure.database.models import (
    DistributionFund,
    JackpotAccount,
    LedgerTransaction,
    Lottery,
    LotteryReserve,
    Ticket,
)


class DailyTransitionService:
    """Activate PLL after every immutable ticket in the shared Daily is settled."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def finalize_if_ready(self) -> bool:
        async with self._session.begin():
            lotteries = list(
                (
                    await self._session.scalars(
                        select(Lottery)
                        .where(Lottery.code.in_(("daily", "pll")))
                        .order_by(Lottery.code)
                        .with_for_update()
                    )
                ).all()
            )
            by_code = {lottery.code: lottery for lottery in lotteries}
            daily = by_code.get("daily")
            pll = by_code.get("pll")
            if daily is None or pll is None or pll.is_active:
                return False
            active_tickets = await self._session.scalar(
                select(func.count(Ticket.id)).where(
                    Ticket.lottery_id == daily.id,
                    Ticket.status == TicketStatus.PURCHASED,
                )
            )
            if active_tickets:
                return False

            await self._move_account(
                daily,
                pll,
                JackpotAccount,
                LedgerAccountKind.JACKPOT,
            )
            await self._move_account(
                daily,
                pll,
                DistributionFund,
                LedgerAccountKind.DISTRIBUTION_FUND,
            )
            await self._move_account(
                daily,
                pll,
                LotteryReserve,
                LedgerAccountKind.LOTTERY_RESERVE,
            )
            daily_jackpot = await self._session.scalar(
                select(JackpotAccount).where(JackpotAccount.lottery_id == daily.id)
            )
            pll_jackpot = await self._session.scalar(
                select(JackpotAccount).where(JackpotAccount.lottery_id == pll.id)
            )
            if daily_jackpot is None or pll_jackpot is None:
                raise RuntimeError("Daily jackpot account is missing.")
            pll_jackpot.base_amount = daily_jackpot.base_amount
            pll.ticket_price = daily.ticket_price
            pll.next_draw_number = max(pll.next_draw_number, daily.next_draw_number)
            pll.next_ticket_number = max(
                pll.next_ticket_number, daily.next_ticket_number
            )
            pll.is_active = True
            daily.is_active = False
            return True

    async def _move_account(
        self,
        daily: Lottery,
        pll: Lottery,
        model: Any,
        kind: LedgerAccountKind,
    ) -> None:
        source = await self._session.scalar(
            select(model).where(model.lottery_id == daily.id).with_for_update()
        )
        target = await self._session.scalar(
            select(model).where(model.lottery_id == pll.id).with_for_update()
        )
        if source is None or target is None:
            raise RuntimeError(f"Daily {kind.value} account is missing.")
        amount = source.balance
        if amount == 0:
            return
        operation_id = uuid4()
        target_before = target.balance
        reason = "shared Daily finalized into independent PLL"
        self._session.add_all(
            [
                LedgerTransaction(
                    id=uuid4(),
                    operation_id=operation_id,
                    idempotency_key=f"daily-transition:{kind.value}:debit",
                    account_kind=kind,
                    account_id=source.id,
                    type=TransactionType.SYSTEM_ADJUSTMENT,
                    amount=-amount,
                    balance_before=amount,
                    balance_after=0,
                    lottery_id=daily.id,
                    details={"reason": reason},
                ),
                LedgerTransaction(
                    id=uuid4(),
                    operation_id=operation_id,
                    idempotency_key=f"daily-transition:{kind.value}:credit",
                    account_kind=kind,
                    account_id=target.id,
                    type=TransactionType.SYSTEM_ADJUSTMENT,
                    amount=amount,
                    balance_before=target_before,
                    balance_after=target_before + amount,
                    lottery_id=pll.id,
                    details={"reason": reason},
                ),
            ]
        )
        source.balance = 0
        source.version += 1
        target.balance += amount
        target.version += 1
