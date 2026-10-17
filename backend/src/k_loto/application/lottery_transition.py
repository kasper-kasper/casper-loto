"""Owner-authorized, atomic lottery-format transitions with full ledgered refunds."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.weekly import draw_configuration_snapshot
from k_loto.domain.enums import (
    AuditAction,
    DrawStatus,
    LedgerAccountKind,
    TicketStatus,
    TransactionType,
)
from k_loto.domain.errors import ConfigurationError, InvalidStateTransition
from k_loto.domain.lottery_rules import GROB_RULES, HALLOWEEN_RULES, LotteryRuleStrategy
from k_loto.infrastructure.database.models import (
    AdminAuditLog,
    Balance,
    Draw,
    JackpotAccount,
    LedgerTransaction,
    Lottery,
    Ticket,
    User,
)


@dataclass(frozen=True, slots=True)
class LotteryFormatTransitionResult:
    refunded_tickets: int
    refunded_cas: int
    converted_draws: int
    already_processed: bool = False


class LotteryFormatTransitionService:
    """Run in a maintenance window with API/bot stopped; no history deletion.

    Row locks also serialize purchases. NOWAIT on draws safely aborts rather
    than deadlocking with the draw-first settlement lock order. A failed check
    rolls back the entire transition, including every compensating entry.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        lottery_code: str = "grob",
        source_rules: LotteryRuleStrategy = GROB_RULES,
        target_rules: LotteryRuleStrategy = HALLOWEEN_RULES,
        ticket_price: int = 6666,
        namespace: str = "halloween-3-28",
    ) -> None:
        self._session = session
        self._lottery_code = lottery_code
        self._source_rules = source_rules
        self._target_rules = target_rules
        self._ticket_price = ticket_price
        self._namespace = namespace

    async def activate(
        self, *, owner_id: UUID, now: datetime | None = None
    ) -> LotteryFormatTransitionResult:
        timestamp = now or datetime.now(UTC)
        async with self._session.begin():
            owner = await self._session.scalar(
                select(User).where(User.id == owner_id, User.is_admin.is_(True))
            )
            if owner is None:
                raise ConfigurationError("Transition requires an owner audit actor.")
            lottery = await self._session.scalar(
                select(Lottery)
                .where(Lottery.code == self._lottery_code)
                .with_for_update()
            )
            if lottery is None:
                raise ConfigurationError("Source lottery is missing.")
            if lottery.ruleset_code == self._target_rules.code:
                return LotteryFormatTransitionResult(0, 0, 0, True)
            if lottery.ruleset_code != self._source_rules.code:
                raise ConfigurationError("Unexpected source ruleset.")
            draws = list(
                (
                    await self._session.scalars(
                        select(Draw)
                        .where(
                            Draw.lottery_id == lottery.id,
                            Draw.status.not_in(
                                (DrawStatus.COMPLETED, DrawStatus.CANCELLED)
                            ),
                        )
                        .order_by(Draw.scheduled_at, Draw.id)
                        .with_for_update(nowait=True)
                    )
                ).all()
            )
            if any(
                draw.scheduled_at <= timestamp
                or draw.status != DrawStatus.SCHEDULED
                or draw.executed_at is not None
                or draw.winning_numbers is not None
                for draw in draws
            ):
                raise InvalidStateTransition(
                    "Recover all due or started draws before format activation."
                )
            tickets = list(
                (
                    await self._session.scalars(
                        select(Ticket)
                        .where(
                            Ticket.lottery_id == lottery.id,
                            Ticket.status == TicketStatus.PURCHASED,
                        )
                        .order_by(Ticket.user_id, Ticket.public_number)
                        .with_for_update()
                    )
                ).all()
            )
            draw_by_id = {draw.id: draw for draw in draws}
            if any(ticket.draw_id not in draw_by_id for ticket in tickets):
                raise InvalidStateTransition(
                    "A purchased ticket is outside future draws."
                )
            jackpot = await self._session.scalar(
                select(JackpotAccount)
                .where(JackpotAccount.lottery_id == lottery.id)
                .with_for_update()
            )
            total = sum(ticket.purchase_price for ticket in tickets)
            if jackpot is None or jackpot.balance < total:
                raise ConfigurationError("Jackpot cannot compensate the full refund.")
            balances = (
                list(
                    (
                        await self._session.scalars(
                            select(Balance)
                            .where(
                                Balance.user_id.in_(
                                    {ticket.user_id for ticket in tickets}
                                )
                            )
                            .order_by(Balance.user_id)
                            .with_for_update()
                        )
                    ).all()
                )
                if tickets
                else []
            )
            balance_by_user = {balance.user_id: balance for balance in balances}
            if any(ticket.user_id not in balance_by_user for ticket in tickets):
                raise ConfigurationError("A ticket owner balance is missing.")
            old_lottery = {
                "name": lottery.name,
                "ruleset_code": lottery.ruleset_code,
                "numbers_to_pick": lottery.numbers_to_pick,
                "max_number": lottery.max_number,
                "ticket_price": lottery.ticket_price,
            }
            reason = (
                f"Owner-approved {self._lottery_code} transition "
                f"to {self._target_rules.code}"
            )
            for ticket in tickets:
                draw = draw_by_id[ticket.draw_id]
                if draw.ticket_count < 1 or draw.total_sales < ticket.purchase_price:
                    raise ConfigurationError(
                        "Future draw sales counters are inconsistent."
                    )
                balance = balance_by_user[ticket.user_id]
                amount = ticket.purchase_price
                operation = uuid4()
                details = {
                    "reason": reason,
                    "source_ruleset": self._source_rules.code,
                    "target_ruleset": self._target_rules.code,
                }
                for kind, account_id, before, delta in (
                    (LedgerAccountKind.JACKPOT, jackpot.id, jackpot.balance, -amount),
                    (
                        LedgerAccountKind.USER_BALANCE,
                        balance.user_id,
                        balance.amount,
                        amount,
                    ),
                ):
                    self._session.add(
                        LedgerTransaction(
                            id=uuid4(),
                            operation_id=operation,
                            idempotency_key=f"{self._namespace}:{ticket.id}:{kind.value}",
                            account_kind=kind,
                            account_id=account_id,
                            type=TransactionType.TICKET_REFUND,
                            amount=delta,
                            balance_before=before,
                            balance_after=before + delta,
                            user_id=ticket.user_id,
                            lottery_id=lottery.id,
                            draw_id=draw.id,
                            ticket_id=ticket.id,
                            details=details,
                        )
                    )
                jackpot.balance -= amount
                jackpot.version += 1
                balance.amount += amount
                balance.version += 1
                ticket.status = TicketStatus.REFUNDED
                ticket.settled_at = timestamp
                draw.ticket_count -= 1
                draw.total_sales -= amount
                self._session.add(
                    AdminAuditLog(
                        id=uuid4(),
                        admin_user_id=owner_id,
                        action=AuditAction.ADJUST,
                        entity_type="ticket",
                        entity_id=ticket.id,
                        old_values={"status": TicketStatus.PURCHASED.value},
                        new_values={
                            "status": TicketStatus.REFUNDED.value,
                            "refund_cas": amount,
                            "operation_id": str(operation),
                        },
                        reason=reason,
                    )
                )
            lottery.name = self._target_rules.label
            lottery.ruleset_code = self._target_rules.code
            lottery.numbers_to_pick = self._target_rules.numbers_to_pick
            lottery.max_number = self._target_rules.max_number
            lottery.ticket_price = self._ticket_price
            for draw in draws:
                if draw.ticket_count != 0 or draw.total_sales != 0:
                    raise ConfigurationError(
                        "Future draw still contains nonrefundable sales."
                    )
                old_snapshot = dict(draw.configuration_snapshot or {})
                if (
                    old_snapshot.get("ruleset_code", self._source_rules.code)
                    != self._source_rules.code
                ):
                    raise ConfigurationError("Unexpected future draw rules snapshot.")
                draw.configuration_snapshot = draw_configuration_snapshot(
                    lottery, jackpot.base_amount
                )
                self._session.add(
                    AdminAuditLog(
                        id=uuid4(),
                        admin_user_id=owner_id,
                        action=AuditAction.UPDATE,
                        entity_type="draw_format",
                        entity_id=draw.id,
                        old_values=old_snapshot,
                        new_values=draw.configuration_snapshot,
                        reason=reason,
                    )
                )
            self._session.add(
                AdminAuditLog(
                    id=uuid4(),
                    admin_user_id=owner_id,
                    action=AuditAction.UPDATE,
                    entity_type="lottery",
                    entity_id=lottery.id,
                    old_values=old_lottery,
                    new_values={
                        "name": lottery.name,
                        "ruleset_code": lottery.ruleset_code,
                        "numbers_to_pick": lottery.numbers_to_pick,
                        "max_number": lottery.max_number,
                        "ticket_price": lottery.ticket_price,
                        "fixed_payouts": dict(self._target_rules.fixed_payouts),
                        "refunded_tickets": len(tickets),
                        "refunded_cas": total,
                    },
                    reason=reason,
                )
            )
            await self._session.flush()
            return LotteryFormatTransitionResult(len(tickets), total, len(draws))
