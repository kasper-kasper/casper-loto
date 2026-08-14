"""Transactional Weekly purchase and settlement services."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.ports import SecureNumberGenerator
from k_loto.domain.draw_state import ensure_draw_transition
from k_loto.domain.enums import (
    DrawStatus,
    LedgerAccountKind,
    LotteryKind,
    TicketStatus,
    TransactionType,
)
from k_loto.domain.errors import (
    ConfigurationError,
    InvalidStateTransition,
    NoAvailableDraw,
)
from k_loto.domain.weekly import (
    SettlementTicket,
    SystemRandomNumberGenerator,
    calculate_weekly_settlement,
    quote_weekly_purchase,
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
)


@dataclass(frozen=True, slots=True)
class PurchaseResult:
    operation_id: UUID
    draw_id: UUID
    ticket_ids: tuple[UUID, ...]
    total_cost: int
    balance_after: int
    already_processed: bool = False


@dataclass(frozen=True, slots=True)
class SettlementResult:
    draw_id: UUID
    winning_numbers: tuple[int, ...]
    total_payout: int
    already_completed: bool = False


def _existing_purchase_result(existing: LedgerTransaction) -> PurchaseResult:
    ticket_ids = tuple(UUID(value) for value in existing.details["ticket_ids"])
    return PurchaseResult(
        operation_id=existing.operation_id,
        draw_id=UUID(existing.details["draw_id"]),
        ticket_ids=ticket_ids,
        total_cost=-existing.amount,
        balance_after=existing.balance_after,
        already_processed=True,
    )


def _ledger_entry(
    *,
    operation_id: UUID,
    idempotency_key: str,
    account_kind: LedgerAccountKind,
    account_id: UUID,
    transaction_type: TransactionType,
    before: int,
    after: int,
    user_id: UUID | None = None,
    lottery_id: UUID | None = None,
    draw_id: UUID | None = None,
    ticket_id: UUID | None = None,
    details: dict[str, Any] | None = None,
) -> LedgerTransaction:
    return LedgerTransaction(
        id=uuid4(),
        operation_id=operation_id,
        idempotency_key=idempotency_key,
        account_kind=account_kind,
        account_id=account_id,
        type=transaction_type,
        amount=after - before,
        balance_before=before,
        balance_after=after,
        user_id=user_id,
        lottery_id=lottery_id,
        draw_id=draw_id,
        ticket_id=ticket_id,
        details=details or {},
    )


class WeeklyTicketPurchaseService:
    """Buy one or more Weekly tickets as one atomic database transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def purchase(
        self,
        *,
        user_id: UUID,
        combinations: list[list[int] | tuple[int, ...]],
        idempotency_key: str,
        now: datetime | None = None,
    ) -> PurchaseResult:
        if not idempotency_key or len(idempotency_key) > 100:
            raise ValueError("idempotency_key must contain 1 to 100 characters.")
        timestamp = now or datetime.now(UTC)
        user_ledger_key = f"purchase:{idempotency_key}:user"

        async with self._session.begin():
            existing = await self._session.scalar(
                select(LedgerTransaction).where(
                    LedgerTransaction.idempotency_key == user_ledger_key
                )
            )
            if existing is not None:
                return _existing_purchase_result(existing)

            lottery = await self._session.scalar(
                select(Lottery)
                .where(
                    Lottery.kind == LotteryKind.WEEKLY,
                    Lottery.is_active.is_(True),
                )
                .with_for_update()
            )
            if lottery is None or lottery.ticket_price is None:
                raise ConfigurationError("Active Weekly lottery is not configured.")
            if lottery.numbers_to_pick != 5 or lottery.max_number != 20:
                raise ConfigurationError("Weekly lottery must use the 5/20 format.")

            existing_after_lock = await self._session.scalar(
                select(LedgerTransaction).where(
                    LedgerTransaction.idempotency_key == user_ledger_key
                )
            )
            if existing_after_lock is not None:
                return _existing_purchase_result(existing_after_lock)

            draw = await self._session.scalar(
                select(Draw)
                .where(
                    Draw.lottery_id == lottery.id,
                    Draw.status == DrawStatus.SCHEDULED,
                    Draw.sales_close_at > timestamp,
                )
                .order_by(Draw.scheduled_at)
                .limit(1)
                .with_for_update()
            )
            if draw is None:
                raise NoAvailableDraw("No Weekly draw is open for sales.")

            balance = await self._session.scalar(
                select(Balance).where(Balance.user_id == user_id).with_for_update()
            )
            if balance is None:
                raise ConfigurationError("User balance account is missing.")
            quote = quote_weekly_purchase(
                combinations, lottery.ticket_price, balance.amount
            )

            jackpot = await self._session.scalar(
                select(JackpotAccount)
                .where(JackpotAccount.lottery_id == lottery.id)
                .with_for_update()
            )
            distribution = await self._session.scalar(
                select(DistributionFund)
                .where(DistributionFund.lottery_id == lottery.id)
                .with_for_update()
            )
            if jackpot is None or distribution is None:
                raise ConfigurationError("Weekly fund accounts are missing.")

            operation_id = uuid4()
            ticket_ids: list[UUID] = []
            first_number = lottery.next_ticket_number
            for offset, combination in enumerate(quote.combinations):
                ticket_id = uuid4()
                ticket_ids.append(ticket_id)
                self._session.add(
                    Ticket(
                        id=ticket_id,
                        public_number=first_number + offset,
                        lottery_id=lottery.id,
                        draw_id=draw.id,
                        user_id=user_id,
                        numbers=list(combination),
                        purchase_price=lottery.ticket_price,
                        purchased_at=timestamp,
                        status=TicketStatus.PURCHASED,
                        prize_amount=0,
                    )
                )
            lottery.next_ticket_number += len(ticket_ids)
            draw.ticket_count += len(ticket_ids)
            draw.total_sales += quote.total_cost

            balance_before = balance.amount
            balance.amount -= quote.total_cost
            balance.version += 1
            jackpot_before = jackpot.balance
            jackpot.balance += quote.jackpot_contribution
            jackpot.version += 1
            distribution_before = distribution.balance
            distribution.balance += quote.distribution_contribution
            distribution.version += 1
            shared_details = {
                "draw_id": str(draw.id),
                "ticket_ids": [str(value) for value in ticket_ids],
                "ticket_count": len(ticket_ids),
            }
            self._session.add_all(
                [
                    _ledger_entry(
                        operation_id=operation_id,
                        idempotency_key=user_ledger_key,
                        account_kind=LedgerAccountKind.USER_BALANCE,
                        account_id=balance.user_id,
                        transaction_type=TransactionType.TICKET_PURCHASE,
                        before=balance_before,
                        after=balance.amount,
                        user_id=user_id,
                        lottery_id=lottery.id,
                        draw_id=draw.id,
                        details=shared_details,
                    ),
                    _ledger_entry(
                        operation_id=operation_id,
                        idempotency_key=f"purchase:{idempotency_key}:jackpot",
                        account_kind=LedgerAccountKind.JACKPOT,
                        account_id=jackpot.id,
                        transaction_type=TransactionType.TICKET_PURCHASE,
                        before=jackpot_before,
                        after=jackpot.balance,
                        user_id=user_id,
                        lottery_id=lottery.id,
                        draw_id=draw.id,
                        details=shared_details,
                    ),
                    _ledger_entry(
                        operation_id=operation_id,
                        idempotency_key=f"purchase:{idempotency_key}:distribution",
                        account_kind=LedgerAccountKind.DISTRIBUTION_FUND,
                        account_id=distribution.id,
                        transaction_type=TransactionType.TICKET_PURCHASE,
                        before=distribution_before,
                        after=distribution.balance,
                        user_id=user_id,
                        lottery_id=lottery.id,
                        draw_id=draw.id,
                        details=shared_details,
                    ),
                ]
            )

        return PurchaseResult(
            operation_id=operation_id,
            draw_id=draw.id,
            ticket_ids=tuple(ticket_ids),
            total_cost=quote.total_cost,
            balance_after=balance.amount,
        )


class WeeklySettlementService:
    """Atomically draw and settle a Weekly draw with row-level locks."""

    def __init__(
        self,
        session: AsyncSession,
        number_generator: SecureNumberGenerator | None = None,
    ) -> None:
        self._session = session
        self._number_generator = number_generator or SystemRandomNumberGenerator()

    async def settle(
        self, draw_id: UUID, *, now: datetime | None = None
    ) -> SettlementResult:
        timestamp = now or datetime.now(UTC)
        async with self._session.begin():
            draw = await self._session.scalar(
                select(Draw).where(Draw.id == draw_id).with_for_update()
            )
            if draw is None:
                raise NoAvailableDraw("Draw does not exist.")
            if draw.status == DrawStatus.COMPLETED:
                return SettlementResult(
                    draw_id=draw.id,
                    winning_numbers=tuple(draw.winning_numbers or ()),
                    total_payout=draw.total_payout,
                    already_completed=True,
                )
            if draw.scheduled_at > timestamp:
                raise InvalidStateTransition(
                    "A draw cannot be settled before scheduled_at."
                )

            lottery = await self._session.scalar(
                select(Lottery).where(Lottery.id == draw.lottery_id).with_for_update()
            )
            if lottery is None or lottery.kind != LotteryKind.WEEKLY:
                raise ConfigurationError("Draw is not attached to a Weekly lottery.")
            jackpot = await self._session.scalar(
                select(JackpotAccount)
                .where(JackpotAccount.lottery_id == lottery.id)
                .with_for_update()
            )
            distribution = await self._session.scalar(
                select(DistributionFund)
                .where(DistributionFund.lottery_id == lottery.id)
                .with_for_update()
            )
            reserve = await self._session.scalar(
                select(LotteryReserve)
                .where(LotteryReserve.lottery_id == lottery.id)
                .with_for_update()
            )
            if jackpot is None or distribution is None or reserve is None:
                raise ConfigurationError("Weekly settlement accounts are missing.")

            ticket_models = list(
                (
                    await self._session.scalars(
                        select(Ticket)
                        .where(Ticket.draw_id == draw.id)
                        .order_by(Ticket.public_number)
                        .with_for_update()
                    )
                ).all()
            )
            winning = self._number_generator.draw(20, 5)
            plan = calculate_weekly_settlement(
                [
                    SettlementTicket(
                        id=ticket.id,
                        public_number=ticket.public_number,
                        user_id=ticket.user_id,
                        numbers=tuple(ticket.numbers),
                        purchase_price=ticket.purchase_price,
                    )
                    for ticket in ticket_models
                ],
                winning,
                distribution_balance=distribution.balance,
                jackpot_balance=jackpot.balance,
                reserve_balance=reserve.balance,
                base_jackpot=jackpot.base_amount,
            )

            user_ids = {ticket.user_id for ticket in ticket_models}
            balances = {
                item.user_id: item
                for item in (
                    await self._session.scalars(
                        select(Balance)
                        .where(Balance.user_id.in_(user_ids))
                        .with_for_update()
                    )
                ).all()
            }
            if set(balances) != user_ids:
                raise ConfigurationError("A winning user balance account is missing.")

            operation_id = uuid4()
            payout_by_ticket = {item.ticket_id: item for item in plan.payouts}
            ledger_entries: list[LedgerTransaction] = []
            for ticket in ticket_models:
                payout = payout_by_ticket[ticket.id]
                ticket.matches = payout.matches
                ticket.prize_amount = payout.amount
                ticket.status = TicketStatus.SETTLED
                ticket.settled_at = timestamp
                if payout.amount == 0:
                    continue
                balance = balances[ticket.user_id]
                before = balance.amount
                balance.amount += payout.amount
                balance.version += 1
                transaction_type = (
                    TransactionType.JACKPOT_PAYOUT
                    if payout.matches == 5
                    else TransactionType.PRIZE_PAYOUT
                )
                ledger_entries.append(
                    _ledger_entry(
                        operation_id=operation_id,
                        idempotency_key=f"draw:{draw.id}:ticket:{ticket.id}:payout",
                        account_kind=LedgerAccountKind.USER_BALANCE,
                        account_id=balance.user_id,
                        transaction_type=transaction_type,
                        before=before,
                        after=balance.amount,
                        user_id=ticket.user_id,
                        lottery_id=lottery.id,
                        draw_id=draw.id,
                        ticket_id=ticket.id,
                        details={"matches": payout.matches},
                    )
                )

            distribution_before = distribution.balance
            distribution.balance = plan.distribution_closing
            distribution.version += 1
            if distribution_before != distribution.balance:
                ledger_entries.append(
                    _ledger_entry(
                        operation_id=operation_id,
                        idempotency_key=f"draw:{draw.id}:distribution:payout",
                        account_kind=LedgerAccountKind.DISTRIBUTION_FUND,
                        account_id=distribution.id,
                        transaction_type=TransactionType.PRIZE_PAYOUT,
                        before=distribution_before,
                        after=distribution.balance,
                        lottery_id=lottery.id,
                        draw_id=draw.id,
                    )
                )
            if plan.reserve_used:
                reserve_before = reserve.balance
                reserve.balance -= plan.reserve_used
                reserve.version += 1
                ledger_entries.append(
                    _ledger_entry(
                        operation_id=operation_id,
                        idempotency_key=f"draw:{draw.id}:reserve:payout",
                        account_kind=LedgerAccountKind.LOTTERY_RESERVE,
                        account_id=reserve.id,
                        transaction_type=TransactionType.PRIZE_PAYOUT,
                        before=reserve_before,
                        after=reserve.balance,
                        lottery_id=lottery.id,
                        draw_id=draw.id,
                    )
                )
            jackpot_before = jackpot.balance
            if plan.jackpot_won:
                if jackpot_before:
                    ledger_entries.append(
                        _ledger_entry(
                            operation_id=operation_id,
                            idempotency_key=f"draw:{draw.id}:jackpot:payout",
                            account_kind=LedgerAccountKind.JACKPOT,
                            account_id=jackpot.id,
                            transaction_type=TransactionType.JACKPOT_PAYOUT,
                            before=jackpot_before,
                            after=0,
                            lottery_id=lottery.id,
                            draw_id=draw.id,
                        )
                    )
                if plan.jackpot_reset_credit:
                    ledger_entries.append(
                        _ledger_entry(
                            operation_id=operation_id,
                            idempotency_key=f"draw:{draw.id}:jackpot:reset",
                            account_kind=LedgerAccountKind.JACKPOT,
                            account_id=jackpot.id,
                            transaction_type=TransactionType.SYSTEM_ADJUSTMENT,
                            before=0,
                            after=plan.jackpot_reset_credit,
                            lottery_id=lottery.id,
                            draw_id=draw.id,
                            details={"reason": "base jackpot reset"},
                        )
                    )
                jackpot.balance = plan.jackpot_closing
                jackpot.version += 1

            ensure_draw_transition(draw.status, DrawStatus.DRAWING)
            ensure_draw_transition(DrawStatus.DRAWING, DrawStatus.SETTLING)
            ensure_draw_transition(DrawStatus.SETTLING, DrawStatus.COMPLETED)
            draw.status = DrawStatus.COMPLETED
            draw.winning_numbers = list(plan.winning_numbers)
            draw.executed_at = timestamp
            draw.total_payout = plan.total_payout
            draw.jackpot_opening = plan.jackpot_opening
            draw.jackpot_closing = plan.jackpot_closing
            draw.distribution_opening = plan.distribution_opening
            draw.distribution_closing = plan.distribution_closing
            draw.reserve_used = plan.reserve_used
            self._session.add_all(ledger_entries)

        return SettlementResult(
            draw_id=draw.id,
            winning_numbers=plan.winning_numbers,
            total_payout=plan.total_payout,
        )
