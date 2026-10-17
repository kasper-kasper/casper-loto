"""Audited, repeatable economy transition while the application is closed."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.economy import ECONOMY_LOCK, control_state
from k_loto.application.weekly import KASPER_FUND_ID
from k_loto.domain.enums import (
    AuditAction,
    DrawStatus,
    LedgerAccountKind,
    TicketStatus,
    TransactionType,
)
from k_loto.domain.errors import ConfigurationError, InvalidStateTransition
from k_loto.domain.lottery_rules import CODE_RULES, FAST_RULES, PULSE_RULES
from k_loto.infrastructure.database.models import (
    AdminAuditLog,
    Balance,
    Draw,
    JackpotAccount,
    KasperFundAccount,
    LedgerTransaction,
    Lottery,
    Ticket,
    User,
)

STEP = "2026-10-fast-economy-v2"


class EconomyTransitionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def audit(
        self,
        owner: UUID,
        kind: str,
        entity: UUID | None,
        old: dict[str, Any],
        new: dict[str, Any],
    ) -> None:
        self.session.add(
            AdminAuditLog(
                id=uuid4(),
                admin_user_id=owner,
                action=AuditAction.ADJUST,
                entity_type=kind,
                entity_id=entity,
                old_values=old,
                new_values=new,
                reason="Owner-approved planned economy transition, October 2026",
            )
        )

    def move(
        self,
        account: Balance | JackpotAccount | KasperFundAccount,
        kind: LedgerAccountKind,
        delta: int,
        *,
        key: str,
        operation: UUID,
        lottery: UUID,
        ticket: Ticket | None = None,
        step: str = STEP,
    ) -> None:
        before = account.amount if isinstance(account, Balance) else account.balance
        if before + delta < 0:
            raise ConfigurationError(
                "Transition compensation would overdraw an account."
            )
        self.session.add(
            LedgerTransaction(
                id=uuid4(),
                operation_id=operation,
                idempotency_key=key,
                account_kind=kind,
                account_id=account.user_id
                if isinstance(account, Balance)
                else account.id,
                type=TransactionType.TICKET_REFUND
                if ticket
                else TransactionType.SYSTEM_ADJUSTMENT,
                amount=delta,
                balance_before=before,
                balance_after=before + delta,
                user_id=ticket.user_id if ticket else None,
                lottery_id=lottery,
                draw_id=ticket.draw_id if ticket else None,
                ticket_id=ticket.id if ticket else None,
                details={
                    "economy_step": step,
                    "reason": "Full refund" if ticket else "Base jackpot reset",
                },
            )
        )
        if isinstance(account, Balance):
            account.amount += delta
        else:
            account.balance += delta
        account.version += 1

    async def activate(self, *, owner_id: UUID, cutoff: datetime) -> dict[str, Any]:
        """The cutoff was persisted when the gateway closed and workers drained."""
        async with self.session.begin():
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": ECONOMY_LOCK}
            )
            owner = await self.session.scalar(
                select(User).where(User.id == owner_id, User.is_admin.is_(True))
            )
            if owner is None:
                raise ConfigurationError("An owner audit actor is required.")
            control = await control_state(self.session)
            if STEP in control.applied_steps:
                if not control.paused:
                    raise InvalidStateTransition(
                        "This transition must not reopen or reclose a later epoch."
                    )
                return {**control.applied_steps[STEP], "already_applied": True}
            lotteries = list(
                (
                    await self.session.scalars(
                        select(Lottery).order_by(Lottery.id).with_for_update()
                    )
                ).all()
            )
            draws = list(
                (
                    await self.session.scalars(
                        select(Draw)
                        .where(
                            Draw.status.not_in(
                                (DrawStatus.COMPLETED, DrawStatus.CANCELLED)
                            )
                        )
                        .order_by(Draw.scheduled_at)
                        .with_for_update()
                    )
                ).all()
            )
            if any(
                d.scheduled_at <= cutoff
                or d.status != DrawStatus.SCHEDULED
                or d.winning_numbers is not None
                or d.executed_at is not None
                for d in draws
            ):
                raise InvalidStateTransition(
                    "Finish all due/started old draws before activating the pause."
                )
            cancellable = {d.id for d in draws}
            tickets = list(
                (
                    await self.session.scalars(
                        select(Ticket)
                        .where(Ticket.status == TicketStatus.PURCHASED)
                        .order_by(Ticket.user_id, Ticket.id)
                        .with_for_update()
                    )
                ).all()
            )
            if any(
                t.draw_id not in cancellable and t.second_draw_id not in cancellable
                for t in tickets
            ):
                raise InvalidStateTransition(
                    "Unsettled ticket is outside the cancelled future draws."
                )
            fund = await self.session.scalar(
                select(KasperFundAccount)
                .where(KasperFundAccount.id == KASPER_FUND_ID)
                .with_for_update()
            )
            if fund is None:
                raise ConfigurationError("Kasper Fund is missing.")
            jackpots = {
                j.lottery_id: j
                for j in (
                    await self.session.scalars(
                        select(JackpotAccount)
                        .order_by(JackpotAccount.id)
                        .with_for_update()
                    )
                ).all()
            }
            balances = {
                b.user_id: b
                for b in (
                    await self.session.scalars(
                        select(Balance)
                        .where(Balance.user_id.in_({t.user_id for t in tickets}))
                        .order_by(Balance.user_id)
                        .with_for_update()
                    )
                ).all()
            }
            by_lottery = {lottery.id: lottery for lottery in lotteries}
            for ticket in tickets:
                operation = uuid4()
                amount = ticket.purchase_price
                jackpot = jackpots[ticket.lottery_id]
                # Dual sales entered the fund. Other old sales entered the jackpot;
                # the fund compensates any part already used by earlier draws.
                from_jackpot = (
                    0
                    if by_lottery[ticket.lottery_id].code == "dual"
                    else min(amount, jackpot.balance)
                )
                if from_jackpot:
                    self.move(
                        jackpot,
                        LedgerAccountKind.JACKPOT,
                        -from_jackpot,
                        key=f"{STEP}:{ticket.id}:jp",
                        operation=operation,
                        lottery=ticket.lottery_id,
                        ticket=ticket,
                    )
                if amount > from_jackpot:
                    self.move(
                        fund,
                        LedgerAccountKind.KASPER_FUND,
                        -(amount - from_jackpot),
                        key=f"{STEP}:{ticket.id}:fund",
                        operation=operation,
                        lottery=ticket.lottery_id,
                        ticket=ticket,
                    )
                self.move(
                    balances[ticket.user_id],
                    LedgerAccountKind.USER_BALANCE,
                    amount,
                    key=f"{STEP}:{ticket.id}:user",
                    operation=operation,
                    lottery=ticket.lottery_id,
                    ticket=ticket,
                )
                ticket.status = TicketStatus.REFUNDED
                ticket.settled_at = datetime.now(UTC)
                self.audit(
                    owner_id,
                    "ticket",
                    ticket.id,
                    {"status": "PURCHASED"},
                    {
                        "status": "REFUNDED",
                        "refund_cas": amount,
                        "operation": str(operation),
                    },
                )
            for draw in draws:
                # Sales counts remain historical facts. Refunded tickets stay linked.
                draw.status = DrawStatus.CANCELLED
                self.audit(
                    owner_id,
                    "draw",
                    draw.id,
                    {"status": "SCHEDULED"},
                    {"status": "CANCELLED", "planned_pause": True},
                )
            terms = {
                "flash": (FAST_RULES, 10_000_000),
                "shadow": (CODE_RULES, 15_000_000),
                "pulse": (PULSE_RULES, 40_000_000),
            }
            for lottery in lotteries:
                if lottery.code in terms:
                    rule, base = terms[lottery.code]
                    jackpot = jackpots[lottery.id]
                    old = {
                        "price": lottery.ticket_price,
                        "rules": lottery.ruleset_code,
                        "base": jackpot.base_amount,
                        "jackpot": jackpot.balance,
                    }
                    delta = base - jackpot.balance
                    operation = uuid4()
                    if delta:
                        self.move(
                            fund,
                            LedgerAccountKind.KASPER_FUND,
                            -delta,
                            key=f"{STEP}:{lottery.id}:fund",
                            operation=operation,
                            lottery=lottery.id,
                        )
                        self.move(
                            jackpot,
                            LedgerAccountKind.JACKPOT,
                            delta,
                            key=f"{STEP}:{lottery.id}:jp",
                            operation=operation,
                            lottery=lottery.id,
                        )
                    jackpot.base_amount = base
                    lottery.ticket_price = 2_000
                    lottery.ruleset_code = rule.code
                    lottery.max_tickets_per_user_per_draw = 500
                    self.audit(
                        owner_id,
                        "lottery_economy",
                        lottery.id,
                        old,
                        {
                            "price": 2000,
                            "rules": rule.code,
                            "base": base,
                            "jackpot": jackpot.balance,
                            "limit": 500,
                            "jackpot_share_cas": 800,
                            "burned_cas": 1200,
                        },
                    )
            if set(terms) - {lottery.code for lottery in lotteries}:
                raise ConfigurationError("A required Fast lottery is missing.")
            if control.epoch == 1:
                control.epoch = 2
                control.epoch_started_at = datetime.now(UTC)
            for lottery in lotteries:
                lottery.economy_epoch = control.epoch
            control.paused = True
            control.pause_started_at = cutoff
            result = {
                "refunded_tickets": len(tickets),
                "refunded_cas": sum(t.purchase_price for t in tickets),
                "cancelled_draws": len(draws),
                "epoch": control.epoch,
                "cutoff": cutoff.isoformat(),
            }
            control.applied_steps = {**control.applied_steps, STEP: result}
            self.audit(owner_id, "economy_pause", None, {"epoch": 1}, result)
            await self.session.flush()
            return result

    async def resume(self, *, owner_id: UUID, now: datetime) -> None:
        """Invoke only after a new, explicit owner instruction. No timed resume."""
        async with self.session.begin():
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": ECONOMY_LOCK}
            )
            owner = await self.session.scalar(
                select(User).where(User.id == owner_id, User.is_admin.is_(True))
            )
            if owner is None:
                raise ConfigurationError("An owner audit actor is required.")
            control = await control_state(self.session)
            if not control.paused:
                return
            pending = await self.session.scalar(
                select(Draw.id)
                .where(Draw.status.not_in((DrawStatus.COMPLETED, DrawStatus.CANCELLED)))
                .limit(1)
            )
            if pending is not None:
                raise InvalidStateTransition(
                    "Resolve all pre-pause draws before reopening."
                )
            control.recovery_after = now
            control.paused = False
            self.audit(
                owner_id,
                "economy_resume",
                None,
                {"paused": True},
                {"paused": False, "skip_slots_until": now.isoformat()},
            )
