"""Transactional Weekly purchase and settlement services."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.ports import SecureNumberGenerator
from k_loto.domain.draw_state import ensure_draw_transition
from k_loto.domain.dual import DUAL_PRICE, DUAL_PURCHASE_DRAW_WINDOW, dual_phase
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
    InsufficientBalance,
    InvalidStateTransition,
    InvalidTicket,
    NoAvailableDraw,
)
from k_loto.domain.lotteries import (
    AUTO_PLAY_ALLOWED_CODES,
    AUTO_PLAY_DRAW_WINDOW,
    draw_display_name,
    is_fast_lottery,
)
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
    BingoPoolTicket,
    Draw,
    JackpotAccount,
    JackpotWinEvent,
    KasperFundAccount,
    LedgerTransaction,
    Lottery,
    NotificationOutbox,
    Ticket,
    User,
    UserNotification,
    UserNotificationPreference,
)

MAX_TICKETS_PER_PURCHASE = 1000
MULTI_DRAW_COUNTS = (1, 5)
KASPER_FUND_ID = UUID("4b415350-4552-4655-4e44-000000000001")


def draw_configuration_snapshot(lottery: Lottery, base_jackpot: int) -> dict[str, Any]:
    """Freeze every setting which can change the price or payout of a draw."""
    snapshot: dict[str, Any] = {
        "ruleset_code": lottery.ruleset_code,
        "ticket_price": lottery.ticket_price,
        "numbers_to_pick": lottery.numbers_to_pick,
        "max_number": lottery.max_number,
        "base_jackpot": base_jackpot,
    }
    if lottery.code == "bingo":
        from k_loto.domain.bingo import JACKPOT_MOVE, TOUR_MOVES

        snapshot["bingo_tour_moves"] = list(TOUR_MOVES)
        snapshot["bingo_jackpot_move"] = JACKPOT_MOVE
    return snapshot


def _snapshot_value(draw: Draw, key: str, fallback: Any) -> Any:
    value = (draw.configuration_snapshot or {}).get(key)
    return fallback if value is None else value


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


def _existing_purchase_result(
    existing: LedgerTransaction, user_id: UUID
) -> PurchaseResult:
    if existing.account_id != user_id:
        raise InvalidTicket("Purchase key belongs to another request.")
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
        draw_count=int(existing.details.get("draw_count", len(draw_ids))),
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
        number_generator: SecureNumberGenerator | None = None,
    ) -> None:
        self._session = session
        self._lottery_code = lottery_code or self.default_lottery_code
        self._target_draw_id = target_draw_id
        self._number_generator = number_generator or SystemRandomNumberGenerator()

    async def purchase(
        self,
        *,
        user_id: UUID,
        combinations: list[list[int] | tuple[int, ...]],
        idempotency_key: str,
        draw_count: int = 1,
        source: TicketSource = TicketSource.MANUAL,
        pool_ticket_ids: list[UUID] | None = None,
        pool_required_numbers: tuple[int, ...] = (),
        select_bingo_pool: bool = False,
        now: datetime | None = None,
    ) -> PurchaseResult:
        if not idempotency_key or len(idempotency_key) > 100:
            raise ValueError("idempotency_key must contain 1 to 100 characters.")
        if draw_count not in MULTI_DRAW_COUNTS:
            raise InvalidTicket("A purchase can cover either 1 or 5 draws.")
        if self._target_draw_id is not None and draw_count != 1:
            raise InvalidTicket("A selected draw purchase cannot span multiple draws.")
        if source == TicketSource.AUTO_PLAY and self._target_draw_id is None:
            raise InvalidTicket("Auto-play requires a selected draw.")
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
                return _existing_purchase_result(existing, user_id)

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
            if (
                source == TicketSource.AUTO_PLAY
                and lottery.code not in AUTO_PLAY_ALLOWED_CODES
            ):
                raise InvalidTicket("Auto-play is not enabled for this lottery.")
            current_rules = _rules_for_lottery(lottery, expected=self.ruleset_code)
            if lottery.code == "bingo" and draw_count != 1:
                raise InvalidTicket("Bingo purchases cover one draw.")
            if lottery.code == "dual" and draw_count != 1:
                raise InvalidTicket("Casper Dual uses one ticket across two rounds.")
            if (
                lottery.numbers_to_pick != current_rules.numbers_to_pick
                or lottery.max_number != current_rules.max_number
            ):
                raise ConfigurationError(
                    f"{self.lottery_label} lottery format is invalid."
                )

            jackpot = await self._session.scalar(
                select(JackpotAccount)
                .where(JackpotAccount.lottery_id == lottery.id)
                .with_for_update()
            )
            if jackpot is None:
                raise ConfigurationError(f"{self.lottery_label} jackpot is missing.")

            existing_after_lock = await self._session.scalar(
                select(LedgerTransaction).where(
                    LedgerTransaction.idempotency_key == user_ledger_key
                )
            )
            if existing_after_lock is not None:
                return _existing_purchase_result(existing_after_lock, user_id)

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
            if self._target_draw_id is not None and (
                lottery.code == "dual" or source == TicketSource.AUTO_PLAY
            ):
                open_draw_ids = list(
                    (
                        await self._session.scalars(
                            select(Draw.id)
                            .where(
                                Draw.lottery_id == lottery.id,
                                Draw.status == DrawStatus.SCHEDULED,
                                Draw.sales_close_at > timestamp,
                            )
                            .order_by(Draw.scheduled_at)
                            .limit(
                                DUAL_PURCHASE_DRAW_WINDOW
                                if lottery.code == "dual"
                                else AUTO_PLAY_DRAW_WINDOW
                            )
                        )
                    ).all()
                )
                eligible_ids = (
                    open_draw_ids[:-1] if lottery.code == "dual" else open_draw_ids
                )
                if draw is None or draw.id not in eligible_ids:
                    raise NoAvailableDraw(
                        "This lottery is limited to the next five draws."
                    )
            if draw is None:
                latest = await self._session.scalar(
                    select(Draw)
                    .where(Draw.lottery_id == lottery.id)
                    .order_by(Draw.scheduled_at.desc())
                    .limit(1)
                )
                schedule_base = latest.scheduled_at if latest is not None else timestamp
                if lottery.code == "dual":
                    schedule_base = max(schedule_base, timestamp)
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
                        lottery.schedule,
                    ),
                    correlation_id=uuid4(),
                    ticket_count=0,
                    total_sales=0,
                    total_payout=0,
                    reserve_used=0,
                    kasper_fund_used=0,
                    configuration_snapshot=draw_configuration_snapshot(
                        lottery, jackpot.base_amount
                    ),
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
                            lottery.schedule,
                        ),
                        correlation_id=uuid4(),
                        ticket_count=0,
                        total_sales=0,
                        total_payout=0,
                        reserve_used=0,
                        kasper_fund_used=0,
                        configuration_snapshot=draw_configuration_snapshot(
                            lottery, jackpot.base_amount
                        ),
                    )
                    lottery.next_draw_number += 1
                    self._session.add(future_draw)
                    draws.append(future_draw)
                    schedule_base = scheduled_at

            dual_second_draw: Draw | None = None
            if lottery.code == "dual":
                if (
                    int(_snapshot_value(draw, "ticket_price", lottery.ticket_price))
                    != DUAL_PRICE
                ):
                    raise ConfigurationError(
                        "Casper Dual ticket price snapshot must be 20,000 CAS."
                    )
                expected_at = next_draw_at(
                    lottery.kind, draw.scheduled_at, lottery.schedule
                )
                dual_second_draw = await self._session.scalar(
                    select(Draw)
                    .where(
                        Draw.lottery_id == lottery.id, Draw.scheduled_at == expected_at
                    )
                    .with_for_update()
                )
                if dual_second_draw is None:
                    dual_second_draw = Draw(
                        id=uuid4(),
                        lottery_id=lottery.id,
                        public_number=lottery.next_draw_number,
                        status=DrawStatus.SCHEDULED,
                        scheduled_at=expected_at,
                        sales_close_at=sales_close_at(
                            lottery.kind,
                            expected_at,
                            lottery.sales_cutoff_minutes,
                            lottery.schedule,
                        ),
                        correlation_id=uuid4(),
                        ticket_count=0,
                        total_sales=0,
                        total_payout=0,
                        reserve_used=0,
                        kasper_fund_used=0,
                        configuration_snapshot=draw_configuration_snapshot(
                            lottery, jackpot.base_amount
                        ),
                    )
                    lottery.next_draw_number += 1
                    self._session.add(dual_second_draw)
                if (
                    dual_second_draw.status != DrawStatus.SCHEDULED
                    or dual_second_draw.scheduled_at <= draw.scheduled_at
                ):
                    raise NoAvailableDraw("Casper Dual second round is unavailable.")
                if dual_phase(draw.scheduled_at) == dual_phase(
                    dual_second_draw.scheduled_at
                ):
                    raise ConfigurationError("Casper Dual rounds must alternate.")
                if draw.sales_close_at <= timestamp:
                    raise NoAvailableDraw(
                        "Casper Dual sales are closed for this round."
                    )

            capacity_draws = draws[:draw_count]
            if dual_second_draw is not None:
                capacity_draws = [*capacity_draws, dual_second_draw]
            for target_draw in capacity_draws:
                existing_count = int(
                    await self._session.scalar(
                        select(func.count(Ticket.id)).where(
                            Ticket.user_id == user_id,
                            (Ticket.draw_id == target_draw.id)
                            | (
                                (Ticket.second_draw_id == target_draw.id)
                                if lottery.code == "dual"
                                else (Ticket.draw_id == target_draw.id)
                            ),
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

            pool_entries: list[BingoPoolTicket] = []
            if lottery.code == "bingo":
                from k_loto.application.bingo import ensure_pool

                await ensure_pool(self._session, lottery, draw)
                pool_query = select(BingoPoolTicket).where(
                    BingoPoolTicket.draw_id == draw.id,
                    BingoPoolTicket.ticket_id.is_(None),
                )
                if pool_ticket_ids is not None:
                    if len(set(pool_ticket_ids)) != len(combinations):
                        raise InvalidTicket("Select distinct Bingo tickets.")
                    pool_query = pool_query.where(
                        BingoPoolTicket.id.in_(pool_ticket_ids)
                    )
                elif source != TicketSource.AUTO_PLAY and not select_bingo_pool:
                    raise InvalidTicket("Bingo requires preprinted ticket IDs.")
                if pool_required_numbers:
                    pool_query = pool_query.where(
                        BingoPoolTicket.numbers.contains(list(pool_required_numbers))
                    )
                pool_entries = list(
                    (
                        await self._session.scalars(
                            pool_query.order_by(BingoPoolTicket.pool_position)
                            .limit(len(combinations))
                            .with_for_update()
                        )
                    ).all()
                )
                if len(pool_entries) != len(combinations):
                    raise NoAvailableDraw(
                        "Some selected Bingo tickets were already purchased."
                    )
                combinations = [entry.numbers for entry in pool_entries]

            fund = None
            if lottery.code == "dual":
                fund = await self._session.scalar(
                    select(KasperFundAccount)
                    .where(KasperFundAccount.id == KASPER_FUND_ID)
                    .with_for_update()
                )
                if fund is None:
                    raise ConfigurationError("Kasper Fund is missing.")
            balance = await self._session.scalar(
                select(Balance).where(Balance.user_id == user_id).with_for_update()
            )
            if balance is None:
                raise ConfigurationError("User balance account is missing.")
            draw_rules = [
                get_lottery_rules(
                    str(_snapshot_value(item, "ruleset_code", current_rules.code))
                )
                for item in draws[:draw_count]
            ]
            if any(item.code != draw_rules[0].code for item in draw_rules[1:]):
                raise InvalidTicket("A purchase cannot span different lottery formats.")
            purchase_rules = draw_rules[0]
            canonical = tuple(
                purchase_rules.validate_purchase_combination(item)
                for item in combinations
            )
            prices = [
                int(_snapshot_value(item, "ticket_price", lottery.ticket_price))
                for item in draws[:draw_count]
            ]
            if any(
                price <= 0 or price % purchase_rules.price_divisor for price in prices
            ):
                raise ConfigurationError("Draw ticket price snapshot is invalid.")
            total_cost = len(canonical) * sum(prices)
            if balance.amount < total_cost:
                raise InsufficientBalance("Insufficient CAS balance.")

            operation_id = uuid4()
            ticket_ids: list[UUID] = []
            first_number = lottery.next_ticket_number
            offset = 0
            for target_draw, ticket_price in zip(
                draws[:draw_count], prices, strict=True
            ):
                for normalized in canonical:
                    stored_numbers = purchase_rules.complete_purchase_combination(
                        normalized, self._number_generator
                    )
                    ticket_id = uuid4()
                    ticket_ids.append(ticket_id)
                    self._session.add(
                        Ticket(
                            id=ticket_id,
                            public_number=first_number + offset,
                            lottery_id=lottery.id,
                            draw_id=target_draw.id,
                            second_draw_id=dual_second_draw.id
                            if dual_second_draw
                            else None,
                            user_id=user_id,
                            numbers=list(stored_numbers),
                            purchase_price=ticket_price,
                            source=source,
                            purchased_at=timestamp,
                            status=TicketStatus.PURCHASED,
                            prize_amount=0,
                        )
                    )
                    offset += 1
                target_draw.ticket_count += len(combinations)
                target_draw.total_sales += len(combinations) * ticket_price
            if dual_second_draw is not None:
                dual_second_draw.ticket_count += len(combinations)
            lottery.next_ticket_number += len(ticket_ids)
            if pool_entries:
                # Persist tickets before setting the inventory foreign keys.
                # The lottery/pool locks remain held until the whole purchase commits.
                await self._session.flush()
                for entry, ticket_id in zip(pool_entries, ticket_ids, strict=True):
                    entry.ticket_id = ticket_id

            balance_before = balance.amount
            balance.amount -= total_cost
            balance.version += 1
            jackpot_before = jackpot.balance
            fund_before = 0
            if lottery.code == "dual":
                assert fund is not None
                fund_before = fund.balance
                fund.balance += total_cost
                fund.version += 1
            else:
                jackpot.balance += total_cost
                jackpot.version += 1
            shared_details = {
                "draw_id": str(draw.id),
                "draw_ids": [str(draw.id), str(dual_second_draw.id)]
                if dual_second_draw
                else [str(value.id) for value in draws[:draw_count]],
                "draw_count": draw_count,
                "combinations_per_draw": len(combinations),
                "ticket_ids": [str(value) for value in ticket_ids],
                "ticket_count": len(ticket_ids),
                "source": source.value,
            }
            purchase_ledger = [
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
                )
            ]
            if jackpot_before != jackpot.balance:
                purchase_ledger.append(
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
                    )
                )
            if fund is not None:
                purchase_ledger.append(
                    _ledger_entry(
                        operation_id=operation_id,
                        idempotency_key=f"purchase:{idempotency_key}:kasper-fund",
                        account_kind=LedgerAccountKind.KASPER_FUND,
                        account_id=fund.id,
                        transaction_type=TransactionType.TICKET_PURCHASE,
                        before=fund_before,
                        after=fund.balance,
                        user_id=user_id,
                        lottery_id=lottery.id,
                        draw_id=draw.id,
                        details=shared_details,
                    )
                )
            self._session.add_all(purchase_ledger)
        return PurchaseResult(
            operation_id=operation_id,
            draw_id=draw.id,
            ticket_ids=tuple(ticket_ids),
            total_cost=total_cost,
            balance_after=balance.amount,
            draw_ids=(draw.id, dual_second_draw.id)
            if dual_second_draw
            else tuple(value.id for value in draws[:draw_count]),
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
            if lottery.code == "dual":
                from k_loto.application.dual import settle_dual_draw

                return await settle_dual_draw(
                    self._session, draw, lottery, timestamp, self._number_generator
                )
            if lottery.code == "bingo":
                from k_loto.domain.bingo import DRAW_MOVES, generate_sequence

                if draw.winning_numbers is None:
                    opening_account = await self._session.scalar(
                        select(JackpotAccount)
                        .where(JackpotAccount.lottery_id == lottery.id)
                        .with_for_update()
                    )
                    if opening_account is None:
                        raise ConfigurationError("Bingo jackpot account is missing.")
                    draw.jackpot_opening = opening_account.balance
                    draw.winning_numbers = list(generate_sequence())
                    missed = timestamp - draw.scheduled_at > timedelta(minutes=5)
                    draw.executed_at = draw.scheduled_at if missed else timestamp
                    draw.status = DrawStatus.DRAWING
                    if not missed:
                        return SettlementResult(draw.id, (), 0, already_completed=True)
                if draw.executed_at and timestamp < draw.executed_at + timedelta(
                    seconds=DRAW_MOVES * 2 + 2
                ):
                    return SettlementResult(draw.id, (), 0, already_completed=True)
            current_rules = _rules_for_lottery(lottery, expected=self.ruleset_code)
            snapshot_rules = str(
                _snapshot_value(draw, "ruleset_code", current_rules.code)
            )
            rules = get_lottery_rules(snapshot_rules)
            if self.ruleset_code is not None and rules.code != self.ruleset_code:
                raise ConfigurationError("Draw rules snapshot is incompatible.")
            jackpot = await self._session.scalar(
                select(JackpotAccount)
                .where(JackpotAccount.lottery_id == lottery.id)
                .with_for_update()
            )
            fund = await self._session.scalar(
                select(KasperFundAccount)
                .where(KasperFundAccount.id == KASPER_FUND_ID)
                .with_for_update()
            )
            if jackpot is None or fund is None:
                raise ConfigurationError(
                    f"{self.lottery_label} settlement accounts are missing."
                )

            ticket_models = list(
                (
                    await self._session.scalars(
                        select(Ticket)
                        .where(
                            Ticket.draw_id == draw.id,
                            Ticket.status == TicketStatus.PURCHASED,
                        )
                        .order_by(Ticket.public_number)
                        .with_for_update()
                    )
                ).all()
            )
            winning = (
                tuple(draw.winning_numbers or ())
                if lottery.code == "bingo"
                else rules.generate_combination(self._number_generator)
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
                distribution_balance=0,
                jackpot_balance=(
                    draw.jackpot_opening
                    if lottery.code == "bingo" and draw.jackpot_opening is not None
                    else jackpot.balance
                ),
                reserve_balance=fund.balance,
                base_jackpot=int(
                    _snapshot_value(draw, "base_jackpot", jackpot.base_amount)
                ),
            )

            if draw.is_distribution:
                from k_loto.domain.distribution import distribute_jackpot

                plan = distribute_jackpot(
                    plan,
                    [
                        SettlementTicket(
                            t.id,
                            t.public_number,
                            t.user_id,
                            tuple(t.numbers),
                            t.purchase_price,
                        )
                        for t in ticket_models
                    ],
                    rules,
                    base_jackpot=int(
                        _snapshot_value(draw, "base_jackpot", jackpot.base_amount)
                    ),
                    fund_balance=fund.balance,
                )
            retained_jackpot = (
                max(jackpot.balance - plan.jackpot_opening, 0)
                if lottery.code == "bingo"
                else 0
            )
            if retained_jackpot:
                plan = replace(
                    plan, jackpot_closing=plan.jackpot_closing + retained_jackpot
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
                if payout.bingo_result is not None:
                    ticket.bingo_result = payout.bingo_result
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
                    if (
                        payout.jackpot_amount > 0
                        if payout.jackpot_amount is not None
                        else payout.matches == rules.jackpot_match
                    )
                    else TransactionType.PRIZE_PAYOUT
                )
                ordinary = payout.amount - (payout.jackpot_amount or 0)
                if payout.jackpot_amount and ordinary:
                    ledger_entries.append(
                        _ledger_entry(
                            operation_id=operation_id,
                            idempotency_key=f"draw:{draw.id}:ticket:{ticket.id}:ordinary",
                            account_kind=LedgerAccountKind.USER_BALANCE,
                            account_id=balance.user_id,
                            transaction_type=TransactionType.PRIZE_PAYOUT,
                            before=before,
                            after=before + ordinary,
                            user_id=ticket.user_id,
                            lottery_id=lottery.id,
                            draw_id=draw.id,
                            ticket_id=ticket.id,
                            details={"bingo": payout.bingo_result},
                        )
                    )
                    before += ordinary
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
                        details={
                            "matches": payout.matches,
                            "distribution_amount": (payout.jackpot_amount or 0)
                            if plan.jackpot_distributed
                            else 0,
                        },
                    )
                )

            if plan.reserve_used:
                fund_before = fund.balance
                fund.balance -= plan.reserve_used
                fund.version += 1
                ledger_entries.append(
                    _ledger_entry(
                        operation_id=operation_id,
                        idempotency_key=f"draw:{draw.id}:kasper-fund:payout",
                        account_kind=LedgerAccountKind.KASPER_FUND,
                        account_id=fund.id,
                        transaction_type=TransactionType.PRIZE_PAYOUT,
                        before=fund_before,
                        after=fund.balance,
                        lottery_id=lottery.id,
                        draw_id=draw.id,
                        details={
                            "ordinary_prizes": plan.reserve_used
                            - plan.jackpot_reset_credit,
                            "jackpot_reset": plan.jackpot_reset_credit,
                        },
                    )
                )
            jackpot_before = jackpot.balance
            if plan.jackpot_won or plan.jackpot_distributed:
                if jackpot_before:
                    ledger_entries.append(
                        _ledger_entry(
                            operation_id=operation_id,
                            idempotency_key=f"draw:{draw.id}:jackpot:payout",
                            account_kind=LedgerAccountKind.JACKPOT,
                            account_id=jackpot.id,
                            transaction_type=TransactionType.JACKPOT_PAYOUT,
                            before=jackpot_before,
                            after=retained_jackpot,
                            lottery_id=lottery.id,
                            draw_id=draw.id,
                            details={
                                "distributed": plan.jackpot_distributed,
                                "category": plan.distribution_category,
                            },
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
                            before=retained_jackpot,
                            after=retained_jackpot + plan.jackpot_reset_credit,
                            lottery_id=lottery.id,
                            draw_id=draw.id,
                            details={"reason": "base jackpot reset"},
                        )
                    )
                jackpot.balance = plan.jackpot_closing
                jackpot.version += 1

            if draw.status != DrawStatus.DRAWING:
                ensure_draw_transition(draw.status, DrawStatus.DRAWING)
            ensure_draw_transition(DrawStatus.DRAWING, DrawStatus.SETTLING)
            ensure_draw_transition(DrawStatus.SETTLING, DrawStatus.COMPLETED)
            draw.status = DrawStatus.COMPLETED
            draw.winning_numbers = list(plan.winning_numbers)
            if lottery.code != "bingo":
                draw.executed_at = timestamp
            draw.total_payout = plan.total_payout
            draw.jackpot_opening = plan.jackpot_opening
            draw.jackpot_closing = plan.jackpot_closing
            draw.distribution_opening = plan.distribution_opening
            draw.distribution_closing = plan.distribution_closing
            draw.reserve_used = 0
            draw.kasper_fund_used = plan.reserve_used
            draw.distribution_category = plan.distribution_category
            draw.distributed_amount = (
                plan.jackpot_opening if plan.jackpot_distributed else 0
            )
            if draw.is_distribution:
                from collections import Counter

                from k_loto.application.distribution import queue_result

                queue_result(
                    self._session,
                    lottery,
                    draw,
                    Counter(p.amount for p in plan.payouts),
                    plan.jackpot_opening
                    if (plan.jackpot_won or plan.jackpot_distributed)
                    else 0,
                    timestamp,
                )
            self._session.add_all(ledger_entries)
            fast_lottery = is_fast_lottery(lottery.code)
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
                jackpot_prize = (
                    0
                    if plan.jackpot_distributed
                    else sum(
                        item.jackpot_amount
                        if item.jackpot_amount is not None
                        else item.amount
                        if item.matches == rules.jackpot_match
                        else 0
                        for item in user_payouts
                    )
                )
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
                    jackpot_prize > 0
                    and preference is not None
                    and preference.telegram_enabled
                ):
                    self._session.add(
                        NotificationOutbox(
                            id=uuid4(),
                            event_key=f"jackpot-win:{draw.id}:user:{user_id}",
                            user_id=user_id,
                            type=NotificationType.JACKPOT_WIN,
                            status=NotificationStatus.PENDING,
                            payload={
                                "lottery_name": payload["lottery_name"],
                                "draw_number": draw.public_number,
                                "scheduled_at": draw.scheduled_at.isoformat(),
                                "win_amount": total_prize,
                            },
                            attempts=0,
                            available_at=timestamp,
                        )
                    )
                if total_prize > 0 and (
                    not fast_lottery or jackpot_prize > 0 or plan.jackpot_distributed
                ):
                    self._session.add(
                        UserNotification(
                            id=uuid4(),
                            event_key=f"result:{draw.id}:user:{user_id}",
                            user_id=user_id,
                            type=InAppNotificationType.WIN,
                            title=f"Выигрыш {total_prize:,} CAS".replace(",", " "),
                            body=(
                                f"{payload['lottery_name']}, тираж "
                                f"№{draw.public_number:04d}. "
                                "Выигрыш уже зачислен."
                            ),
                            payload=payload,
                            created_at=timestamp,
                        )
                    )

            if plan.jackpot_won and plan.jackpot_opening > 0:
                jackpot_payouts = [
                    item
                    for item in plan.payouts
                    if (
                        item.jackpot_amount > 0
                        if item.jackpot_amount is not None
                        else item.matches == rules.jackpot_match
                    )
                ]
                winner_ids = {item.user_id for item in jackpot_payouts}
                self._session.add(
                    JackpotWinEvent(
                        id=uuid4(),
                        draw_id=draw.id,
                        lottery_id=lottery.id,
                        jackpot_amount=plan.jackpot_opening,
                        winner_ticket_count=len(jackpot_payouts),
                        winner_user_count=len(winner_ids),
                        base_jackpot_after=plan.jackpot_closing,
                        occurred_at=timestamp,
                    )
                )
                if not fast_lottery:
                    recipients = (
                        await self._session.scalars(
                            select(User.id).where(
                                User.is_active.is_(True), User.is_admin.is_(False)
                            )
                        )
                    ).all()
                    display_name = draw_display_name(
                        lottery.code, lottery.name, draw.scheduled_at
                    )
                    formatted_amount = f"{plan.jackpot_opening:,}".replace(",", " ")
                    for recipient_id in recipients:
                        self._session.add(
                            UserNotification(
                                id=uuid4(),
                                event_key=f"jackpot:{draw.id}:user:{recipient_id}",
                                user_id=recipient_id,
                                type=InAppNotificationType.JACKPOT_NEWS,
                                title="Джекпот сорван!",
                                body=(
                                    f"В {display_name}, тираж "
                                    f"№{draw.public_number:04d}, разыграно "
                                    f"{formatted_amount} CAS. Джекпот восстановлен."
                                ),
                                payload={
                                    "lottery_code": lottery.code,
                                    "lottery_name": display_name,
                                    "draw_number": draw.public_number,
                                    "jackpot_amount": plan.jackpot_opening,
                                    "winner_ticket_count": len(jackpot_payouts),
                                    "winner_user_count": len(winner_ids),
                                    "base_jackpot_after": plan.jackpot_closing,
                                },
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
