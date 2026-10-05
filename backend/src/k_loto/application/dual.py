"""Transactional settlement for one Casper Dual ticket spanning two draws."""

from datetime import datetime
from typing import cast
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.weekly import KASPER_FUND_ID, SettlementResult, _ledger_entry
from k_loto.domain.draw_state import ensure_draw_transition
from k_loto.domain.dual import (
    DUAL_JACKPOT,
    dual_match_code,
    dual_matches,
    dual_phase,
    dual_prize,
)
from k_loto.domain.enums import (
    DrawStatus,
    InAppNotificationType,
    LedgerAccountKind,
    TicketStatus,
    TransactionType,
)
from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientReserve,
    InvalidStateTransition,
)
from k_loto.domain.lottery_rules import DUAL_RULES, NumberGenerator
from k_loto.infrastructure.database.models import (
    Balance,
    Draw,
    JackpotAccount,
    JackpotWinEvent,
    KasperFundAccount,
    Lottery,
    Ticket,
    UserNotification,
)


async def settle_dual_draw(
    session: AsyncSession,
    draw: Draw,
    lottery: Lottery,
    timestamp: datetime,
    generator: NumberGenerator,
) -> SettlementResult:
    """Settle a Dual draw under the common draw and lottery locks."""
    if draw.status == DrawStatus.COMPLETED:
        return SettlementResult(
            draw.id,
            tuple(draw.winning_numbers or ()),
            draw.total_payout,
            already_completed=True,
        )
    snapshot = draw.configuration_snapshot or {}
    if snapshot.get("ruleset_code", lottery.ruleset_code) != DUAL_RULES.code:
        raise ConfigurationError("Casper Dual draw rules snapshot is invalid.")
    phase = dual_phase(draw.scheduled_at)
    winning = tuple(generator.draw(12, 2))
    tickets = list(
        (
            await session.scalars(
                select(Ticket)
                .where(
                    Ticket.lottery_id == lottery.id,
                    Ticket.status == TicketStatus.PURCHASED,
                    or_(Ticket.draw_id == draw.id, Ticket.second_draw_id == draw.id),
                )
                .order_by(Ticket.public_number)
                .with_for_update()
            )
        ).all()
    )
    completed: list[tuple[Ticket, int]] = []
    for ticket in tickets:
        count = dual_matches(ticket.numbers, winning, phase)
        if phase == "NIGHT":
            ticket.dual_night_matches = count
        else:
            ticket.dual_dawn_matches = count
        if ticket.second_draw_id == draw.id:
            first = await session.get(Draw, ticket.draw_id)
            if (
                first is None
                or first.status != DrawStatus.COMPLETED
                or first.winning_numbers is None
            ):
                raise InvalidStateTransition(
                    "Casper Dual first round must finish before the second."
                )
            if ticket.dual_night_matches is None or ticket.dual_dawn_matches is None:
                raise InvalidStateTransition(
                    "Casper Dual first-round result is missing."
                )
            completed.append(
                (
                    ticket,
                    dual_prize(ticket.dual_night_matches, ticket.dual_dawn_matches),
                )
            )
    total_payout = sum(amount for _, amount in completed)
    jackpot_winners = [ticket for ticket, amount in completed if amount == DUAL_JACKPOT]
    jackpot = await session.scalar(
        select(JackpotAccount)
        .where(JackpotAccount.lottery_id == lottery.id)
        .with_for_update()
    )
    if (
        jackpot is None
        or jackpot.balance != DUAL_JACKPOT
        or jackpot.base_amount != DUAL_JACKPOT
    ):
        raise ConfigurationError("Casper Dual fixed jackpot account is invalid.")
    fund = await session.scalar(
        select(KasperFundAccount)
        .where(KasperFundAccount.id == KASPER_FUND_ID)
        .with_for_update()
    )
    if fund is None:
        raise ConfigurationError("Kasper Fund is missing.")
    if fund.balance < total_payout:
        raise InsufficientReserve("Kasper Fund cannot cover Casper Dual prizes.")
    user_ids = {ticket.user_id for ticket, amount in completed if amount > 0}
    balances = (
        {
            item.user_id: item
            for item in (
                await session.scalars(
                    select(Balance)
                    .where(Balance.user_id.in_(user_ids))
                    .with_for_update()
                )
            ).all()
        }
        if user_ids
        else {}
    )
    if set(balances) != user_ids:
        raise ConfigurationError("A Casper Dual winner balance is missing.")
    operation_id = uuid4()
    for ticket, amount in completed:
        ticket.matches = dual_match_code(
            cast(int, ticket.dual_night_matches), cast(int, ticket.dual_dawn_matches)
        )
        ticket.prize_amount = amount
        ticket.status = TicketStatus.SETTLED
        ticket.settled_at = timestamp
        if not amount:
            continue
        balance = balances[ticket.user_id]
        before = balance.amount
        balance.amount += amount
        balance.version += 1
        is_jackpot = amount == DUAL_JACKPOT
        session.add(
            _ledger_entry(
                operation_id=operation_id,
                idempotency_key=f"dual:{draw.id}:ticket:{ticket.id}:payout",
                account_kind=LedgerAccountKind.USER_BALANCE,
                account_id=balance.user_id,
                transaction_type=TransactionType.JACKPOT_PAYOUT
                if is_jackpot
                else TransactionType.PRIZE_PAYOUT,
                before=before,
                after=balance.amount,
                user_id=ticket.user_id,
                lottery_id=lottery.id,
                draw_id=draw.id,
                ticket_id=ticket.id,
                details={
                    "night_matches": ticket.dual_night_matches,
                    "dawn_matches": ticket.dual_dawn_matches,
                },
            )
        )
        session.add(
            UserNotification(
                id=uuid4(),
                event_key=f"dual-result:{ticket.id}",
                user_id=ticket.user_id,
                type=InAppNotificationType.WIN,
                title=f"Casper Dual: +{amount:,} CAS".replace(",", " "),
                body=(
                    f"Билет №{ticket.public_number}. Оба раунда завершены; "
                    "выигрыш зачислен."
                ),
                payload={
                    "lottery_code": "dual",
                    "ticket_id": str(ticket.id),
                    "draw_number": draw.public_number,
                    "prize_amount": amount,
                },
                created_at=timestamp,
            )
        )
    if total_payout:
        before = fund.balance
        fund.balance -= total_payout
        fund.version += 1
        session.add(
            _ledger_entry(
                operation_id=operation_id,
                idempotency_key=f"dual:{draw.id}:kasper-fund:payout",
                account_kind=LedgerAccountKind.KASPER_FUND,
                account_id=fund.id,
                transaction_type=TransactionType.PRIZE_PAYOUT,
                before=before,
                after=fund.balance,
                lottery_id=lottery.id,
                draw_id=draw.id,
                details={
                    "completed_tickets": len(completed),
                    "fixed_jackpot": DUAL_JACKPOT,
                },
            )
        )
    if jackpot_winners:
        # The first jackpot is paid by its dedicated account, then restored from
        # the Kasper Fund. Additional same-draw winners are fund-backed at 5m each.
        session.add(
            _ledger_entry(
                operation_id=operation_id,
                idempotency_key=f"dual:{draw.id}:jackpot:payout",
                account_kind=LedgerAccountKind.JACKPOT,
                account_id=jackpot.id,
                transaction_type=TransactionType.JACKPOT_PAYOUT,
                before=DUAL_JACKPOT,
                after=0,
                lottery_id=lottery.id,
                draw_id=draw.id,
                details={"winner_ticket_count": len(jackpot_winners)},
            )
        )
        session.add(
            _ledger_entry(
                operation_id=operation_id,
                idempotency_key=f"dual:{draw.id}:jackpot:refill",
                account_kind=LedgerAccountKind.JACKPOT,
                account_id=jackpot.id,
                transaction_type=TransactionType.SYSTEM_ADJUSTMENT,
                before=0,
                after=DUAL_JACKPOT,
                lottery_id=lottery.id,
                draw_id=draw.id,
                details={"reason": "fixed Casper Dual jackpot refill"},
            )
        )
        jackpot.version += 1
        session.add(
            JackpotWinEvent(
                id=uuid4(),
                draw_id=draw.id,
                lottery_id=lottery.id,
                jackpot_amount=DUAL_JACKPOT * len(jackpot_winners),
                winner_ticket_count=len(jackpot_winners),
                winner_user_count=len({ticket.user_id for ticket in jackpot_winners}),
                base_jackpot_after=DUAL_JACKPOT,
                occurred_at=timestamp,
            )
        )
    if draw.status != DrawStatus.DRAWING:
        ensure_draw_transition(draw.status, DrawStatus.DRAWING)
    ensure_draw_transition(DrawStatus.DRAWING, DrawStatus.SETTLING)
    ensure_draw_transition(DrawStatus.SETTLING, DrawStatus.COMPLETED)
    draw.status = DrawStatus.COMPLETED
    draw.winning_numbers = list(winning)
    draw.executed_at = timestamp
    draw.total_payout = total_payout
    draw.jackpot_opening = DUAL_JACKPOT
    draw.jackpot_closing = DUAL_JACKPOT
    draw.distribution_opening = 0
    draw.distribution_closing = 0
    draw.reserve_used = 0
    draw.kasper_fund_used = total_payout
    return SettlementResult(draw.id, winning, total_payout)
