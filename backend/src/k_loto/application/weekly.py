"""Transactional Weekly purchase and settlement services."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.ports import SecureNumberGenerator
from k_loto.domain.draw_state import ensure_draw_transition
from k_loto.domain.enums import (
    DrawStatus,
    InAppNotificationType,
    LedgerAccountKind,
    LotteryKind,
    NotificationStatus,
    NotificationType,
    TicketSource,
    TicketStatus,
    TransactionType,
)
from k_loto.domain.errors import (
    ConfigurationError,
    InvalidStateTransition,
    InvalidTicket,
    NoAvailableDraw,
)
from k_loto.domain.lotteries import draw_display_name
from k_loto.domain.lottery_rules import (
    DAILY_RULES,
    WEEKLY_RULES,
    LotteryRuleStrategy,
    get_lottery_rules,
)
from k_loto.domain.schedules import next_draw_at, sales_close_at
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
    NotificationOutbox,
    Ticket,
    UserNotification,
    UserNotificationPreference,
)

MAX_TICKETS_PER_PURCHASE = 1000
MULTI_DRAW_COUNTS = (1, 5)


def _rules_for_lottery(
    lottery: Lottery, *, expected: str | None
) -> LotteryRuleStrategy:
    """Resolve persisted rules; legacy in-memory objects get a safe fallback."""
    stored = getattr(lottery, "ruleset_code", None)
    if not stored:
        stored = (
            WEEKLY_RULES.code
            if lottery.kind == LotteryKind.WEEKLY
            else DAILY_RULES.code
        )
    if expected is not None and stored != expected:
        raise ConfigurationError(
            f"Lottery uses {stored!r}, expected rule strategy {expected!r}."
        )
    return get_lottery_rules(stored)


@dataclass(frozen=True, slots=True)
class PurchaseResult:
    operation_id: UUID
    draw_id: UUID
    ticket_ids: tuple[UUID, ...]
    total_cost: int
    balance_after: int
    draw_ids: tuple[UUID, ...] = ()
    draw_count: int = 1
    already_processed: bool = False


@dataclass(frozen=True, slots=True)
class SettlementResult:
    draw_id: UUID
    winning_numbers: tuple[int, ...]
    total_payout: int
    already_completed: bool = False


def _existing_purchase_result(existing: LedgerTransaction) -> PurchaseResult:
    ticket_ids = tuple(UUID(value) for value in existing.details["ticket_ids"])
    draw_ids = tuple(
        UUID(value)
        for value in existing.details.get("draw_ids", [existing.details["draw_id"]])
    )
    return PurchaseResult(
        operation_id=existing.operation_id,
        draw_id=UUID(existing.details["draw_id"]),
        ticket_ids=ticket_ids,
        total_cost=-existing.amount,
        balance_after=existing.balance_after,
        draw_ids=draw_ids,
        draw_count=len(draw_ids),
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

    lottery_kind = LotteryKind.WEEKLY
    numbers_to_pick = 5
    max_number = 20
    quote_purchase = staticmethod(quote_weekly_purchase)
    lottery_label = "Weekly"
    default_lottery_code = "weekly"
    ruleset_code: str | None = WEEKLY_RULES.code

    def __init__(
        self,
        session: AsyncSession,
        lottery_code: str | None = None,
        target_draw_id: UUID | None = None,
    ) -> None:
        self._session = session
        self._lottery_code = lottery_code or self.default_lottery_code
        self._target_draw_id = target_draw_id

    async def purchase(
        self,
        *,
        user_id: UUID,
        combinations: list[list[int] | tuple[int, ...]],
        idempotency_key: str,
        draw_count: int = 1,
        source: TicketSource = TicketSource.MANUAL,
        now: datetime | None = None,
    ) -> PurchaseResult:
        if not idempotency_key or len(idempotency_key) > 100:
            raise ValueError("idempotency_key must contain 1 to 100 characters.")
        if draw_count not in MULTI_DRAW_COUNTS:
            raise InvalidTicket("A purchase can cover either 1 or 5 draws.")
        if self._target_draw_id is not None and draw_count != 1:
            raise InvalidTicket("A selected draw purchase cannot span multiple draws.")
        if not 1 <= len(combinations) <= MAX_TICKETS_PER_PURCHASE:
            raise InvalidTicket(
                f"A purchase must contain 1 to {MAX_TICKETS_PER_PURCHASE} tickets."
            )
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
                    Lottery.code == self._lottery_code,
                    Lottery.is_active.is_(True),
                )
                .with_for_update()
            )
            if lottery is None or lottery.ticket_price is None:
                raise ConfigurationError(
                    f"Active {self.lottery_label} lottery is not configured."
                )
            rules = _rules_for_lottery(lottery, expected=self.ruleset_code)
            if (
                lottery.numbers_to_pick != rules.numbers_to_pick
                or lottery.max_number != rules.max_number
            ):
                raise ConfigurationError(
                    f"{self.lottery_label} lottery format is invalid."
                )

            existing_after_lock = await self._session.scalar(
                select(LedgerTransaction).where(
                    LedgerTransaction.idempotency_key == user_ledger_key
                )
            )
            if existing_after_lock is not None:
                return _existing_purchase_result(existing_after_lock)

            if len(combinations) > lottery.max_tickets_per_purchase:
                raise InvalidTicket(
                    f"This lottery accepts at most {lottery.max_tickets_per_purchase} "
                    "tickets in one purchase."
                )

            draw_query = select(Draw).where(
                Draw.lottery_id == lottery.id,
                Draw.status == DrawStatus.SCHEDULED,
                Draw.sales_close_at > timestamp,
            )
            if self._target_draw_id is not None:
                draw_query = draw_query.where(Draw.id == self._target_draw_id)
            else:
                draw_query = draw_query.order_by(Draw.scheduled_at).limit(draw_count)
            if draw_count == 1:
                one_draw = await self._session.scalar(draw_query.with_for_update())
                draws = [one_draw] if one_draw is not None else []
            else:
                draws = list(
                    (await self._session.scalars(draw_query.with_for_update())).all()
                )
            draw = draws[0] if draws else None
            if draw is None and self._target_draw_id is not None:
                raise NoAvailableDraw(
                    "The selected draw is no longer available for ticket sales."
                )
            if draw is None:
                latest = await self._session.scalar(
                    select(Draw)
                    .where(Draw.lottery_id == lottery.id)
                    .order_by(Draw.scheduled_at.desc())
                    .limit(1)
                )
                schedule_base = latest.scheduled_at if latest is not None else timestamp
                scheduled_at = next_draw_at(
                    lottery.kind, schedule_base, lottery.schedule
                )
                draw = Draw(
                    id=uuid4(),
                    lottery_id=lottery.id,
                    public_number=lottery.next_draw_number,
                    status=DrawStatus.SCHEDULED,
                    scheduled_at=scheduled_at,
                    sales_close_at=sales_close_at(
                        lottery.kind,
                        scheduled_at,
                        lottery.sales_cutoff_minutes,
                    ),
                    correlation_id=uuid4(),
                    ticket_count=0,
                    total_sales=0,
                    total_payout=0,
                    reserve_used=0,
                )
                lottery.next_draw_number += 1
                self._session.add(draw)
                draws.append(draw)

            if draw_count > 1:
                latest = await self._session.scalar(
                    select(Draw)
                    .where(Draw.lottery_id == lottery.id)
                    .order_by(Draw.scheduled_at.desc())
                    .limit(1)
                )
                schedule_base = (
                    latest.scheduled_at if latest is not None else draw.scheduled_at
                )
                while len(draws) < draw_count:
                    scheduled_at = next_draw_at(
                        lottery.kind, schedule_base, lottery.schedule
                    )
                    future_draw = Draw(
                        id=uuid4(),
                        lottery_id=lottery.id,
                        public_number=lottery.next_draw_number,
                        status=DrawStatus.SCHEDULED,
                        scheduled_at=scheduled_at,
                        sales_close_at=sales_close_at(
                            lottery.kind,
                            scheduled_at,
                            lottery.sales_cutoff_minutes,
                        ),
                        correlation_id=uuid4(),
                        ticket_count=0,
                        total_sales=0,
                        total_payout=0,
                        reserve_used=0,
                    )
                    lottery.next_draw_number += 1
                    self._session.add(future_draw)
                    draws.append(future_draw)
                    schedule_base = scheduled_at

            for target_draw in draws[:draw_count]:
                existing_count = int(
                    await self._session.scalar(
                        select(func.count(Ticket.id)).where(
                            Ticket.user_id == user_id,
                            Ticket.draw_id == target_draw.id,
                        )
                    )
                    or 0
                )
                if (
                    existing_count + len(combinations)
                    > lottery.max_tickets_per_user_per_draw
                ):
                    raise InvalidTicket(
                        "The per-player ticket limit for this draw would be exceeded."
                    )

            balance = await self._session.scalar(
                select(Balance).where(Balance.user_id == user_id).with_for_update()
            )
            if balance is None:
                raise ConfigurationError("User balance account is missing.")
            expanded_combinations = combinations * draw_count
            quote = rules.quote_purchase(
                expanded_combinations, lottery.ticket_price, balance.amount
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
                raise ConfigurationError(
                    f"{self.lottery_label} fund accounts are missing."
                )

            operation_id = uuid4()
            ticket_ids: list[UUID] = []
            first_number = lottery.next_ticket_number
            offset = 0
            for target_draw in draws[:draw_count]:
                for combination in combinations:
                    normalized = tuple(sorted(combination))
                    ticket_id = uuid4()
                    ticket_ids.append(ticket_id)
                    self._session.add(
                        Ticket(
                            id=ticket_id,
                            public_number=first_number + offset,
                            lottery_id=lottery.id,
                            draw_id=target_draw.id,
                            user_id=user_id,
                            numbers=list(normalized),
                            purchase_price=lottery.ticket_price,
                            source=source,
                            purchased_at=timestamp,
                            status=TicketStatus.PURCHASED,
                            prize_amount=0,
                        )
                    )
                    offset += 1
                target_draw.ticket_count += len(combinations)
                target_draw.total_sales += len(combinations) * lottery.ticket_price
            lottery.next_ticket_number += len(ticket_ids)

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
                "draw_ids": [str(value.id) for value in draws[:draw_count]],
                "draw_count": draw_count,
                "combinations_per_draw": len(combinations),
                "ticket_ids": [str(value) for value in ticket_ids],
                "ticket_count": len(ticket_ids),
                "source": source.value,
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
            draw_ids=tuple(value.id for value in draws[:draw_count]),
            draw_count=draw_count,
        )


class WeeklySettlementService:
    """Atomically draw and settle a Weekly draw with row-level locks."""

    lottery_kind = LotteryKind.WEEKLY
    numbers_to_pick = 5
    max_number = 20
    calculate_settlement = staticmethod(calculate_weekly_settlement)
    lottery_label = "Weekly"
    ruleset_code: str | None = WEEKLY_RULES.code

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
            if lottery is None:
                raise ConfigurationError(
                    f"Draw is not attached to a {self.lottery_label} lottery."
                )
            rules = _rules_for_lottery(lottery, expected=self.ruleset_code)
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
                raise ConfigurationError(
                    f"{self.lottery_label} settlement accounts are missing."
                )

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
            winning = self._number_generator.draw(
                rules.max_number, rules.numbers_to_pick
            )
            plan = rules.calculate_settlement(
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
                    if payout.matches == rules.jackpot_match
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
            preferences = {
                preference.user_id: preference
                for preference in (
                    await self._session.scalars(
                        select(UserNotificationPreference).where(
                            UserNotificationPreference.user_id.in_(user_ids)
                        )
                    )
                ).all()
            }
            for user_id in sorted(user_ids, key=lambda value: value.int):
                user_tickets = [
                    ticket for ticket in ticket_models if ticket.user_id == user_id
                ]
                user_payouts = [payout_by_ticket[ticket.id] for ticket in user_tickets]
                total_prize = sum(item.amount for item in user_payouts)
                payload = {
                    "lottery_code": lottery.code,
                    "lottery_name": draw_display_name(
                        lottery.code, lottery.name, draw.scheduled_at
                    ),
                    "draw_number": draw.public_number,
                    "scheduled_at": draw.scheduled_at.isoformat(),
                    "winning_numbers": list(plan.winning_numbers),
                    "tickets": [
                        {
                            "public_number": ticket.public_number,
                            "numbers": list(ticket.numbers),
                            "matches": payout_by_ticket[ticket.id].matches,
                            "prize": payout_by_ticket[ticket.id].amount,
                        }
                        for ticket in user_tickets
                    ],
                    "total_prize": total_prize,
                    "prize_fund": plan.jackpot_closing,
                    "draw_total_payout": plan.total_payout,
                    "balance_after": balances[user_id].amount,
                }
                preference = preferences.get(user_id)
                if (
                    preference is not None
                    and preference.telegram_enabled
                    and preference.draw_results_enabled
                ):
                    self._session.add(
                        NotificationOutbox(
                            id=uuid4(),
                            event_key=f"result:{draw.id}:user:{user_id}",
                            user_id=user_id,
                            type=NotificationType.DRAW_RESULT,
                            status=NotificationStatus.PENDING,
                            payload=payload,
                            attempts=0,
                            available_at=timestamp,
                        )
                    )
                if total_prize > 0:
                    self._session.add(
                        UserNotification(
                            id=uuid4(),
                            event_key=f"win:{draw.id}:user:{user_id}",
                            user_id=user_id,
                            type=InAppNotificationType.WIN,
                            title=f"Выигрыш {total_prize:,} CAS".replace(",", " "),
                            body=(
                                f"{payload['lottery_name']}, тираж "
                                f"№{draw.public_number:04d}. Выигрыш уже зачислен."
                            ),
                            payload=payload,
                            created_at=timestamp,
                        )
                    )

        return SettlementResult(
            draw_id=draw.id,
            winning_numbers=plan.winning_numbers,
            total_payout=plan.total_payout,
        )


class LotteryTicketPurchaseService(WeeklyTicketPurchaseService):
    """Purchase service whose rule strategy is selected by the lottery entity."""

    ruleset_code = None
    lottery_label = "Configured"


class LotterySettlementService(WeeklySettlementService):
    """Settlement service whose rule strategy is selected by the lottery entity."""

    ruleset_code = None
    lottery_label = "Configured"
