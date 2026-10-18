"""Shared audited application of approved batches during the planned pause."""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.economy import ECONOMY_LOCK, control_state
from k_loto.application.economy_transition import (
    STEP as PAUSE_STEP,
)
from k_loto.application.economy_transition import (
    EconomyTransitionService,
)
from k_loto.application.weekly import KASPER_FUND_ID
from k_loto.domain.enums import DrawStatus, LedgerAccountKind, TicketStatus
from k_loto.domain.errors import ConfigurationError, InvalidStateTransition
from k_loto.domain.lottery_rules import LotteryRuleStrategy
from k_loto.infrastructure.database.models import (
    Draw,
    JackpotAccount,
    KasperFundAccount,
    Lottery,
    Ticket,
    User,
)

EconomyTerms = tuple[tuple[str, LotteryRuleStrategy, int, int], ...]


class PausedEconomyBatchService:
    step: str
    terms: EconomyTerms
    per_draw_limit: int

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def apply(self, *, owner_id: UUID) -> dict[str, Any]:
        """No refunds, new epoch, counter reset or reopening in this batch."""
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
            if not control.paused or PAUSE_STEP not in control.applied_steps:
                raise InvalidStateTransition(
                    "Apply only after the planned pause and initial refunds."
                )
            if self.step in control.applied_steps:
                return {**control.applied_steps[self.step], "already_applied": True}
            pending_draw = await self.session.scalar(
                select(Draw.id)
                .where(Draw.status.not_in((DrawStatus.COMPLETED, DrawStatus.CANCELLED)))
                .limit(1)
            )
            pending_ticket = await self.session.scalar(
                select(Ticket.id)
                .where(Ticket.status == TicketStatus.PURCHASED)
                .limit(1)
            )
            if pending_draw is not None or pending_ticket is not None:
                raise InvalidStateTransition("Resolve all old obligations first.")
            lotteries = {
                lottery.code: lottery
                for lottery in (
                    await self.session.scalars(
                        select(Lottery)
                        .where(Lottery.code.in_([term[0] for term in self.terms]))
                        .order_by(Lottery.id)
                        .with_for_update()
                    )
                ).all()
            }
            if set(lotteries) != {term[0] for term in self.terms}:
                raise ConfigurationError("A required lottery is missing.")
            fund = await self.session.scalar(
                select(KasperFundAccount)
                .where(KasperFundAccount.id == KASPER_FUND_ID)
                .with_for_update()
            )
            jackpots = {
                jackpot.lottery_id: jackpot
                for jackpot in (
                    await self.session.scalars(
                        select(JackpotAccount)
                        .where(
                            JackpotAccount.lottery_id.in_(
                                [x.id for x in lotteries.values()]
                            )
                        )
                        .order_by(JackpotAccount.id)
                        .with_for_update()
                    )
                ).all()
            }
            if fund is None or set(jackpots) != {x.id for x in lotteries.values()}:
                raise ConfigurationError("Required economy accounts are missing.")
            for code, rule, _, _ in self.terms:
                lottery = lotteries[code]
                if (lottery.numbers_to_pick, lottery.max_number) != (
                    rule.numbers_to_pick,
                    rule.max_number,
                ):
                    raise ConfigurationError(
                        "The approved lottery format must not change."
                    )
            # Return excess jackpots first, so funding does not depend on term order.
            changes = sorted(
                self.terms,
                key=lambda term: term[3] - jackpots[lotteries[term[0]].id].balance,
            )
            movements = EconomyTransitionService(self.session)
            for code, rule, price, base in changes:
                lottery = lotteries[code]
                jackpot = jackpots[lottery.id]
                old = {
                    "price": lottery.ticket_price,
                    "rules": lottery.ruleset_code,
                    "base": jackpot.base_amount,
                    "jackpot": jackpot.balance,
                    "per_purchase": lottery.max_tickets_per_purchase,
                    "per_draw": lottery.max_tickets_per_user_per_draw,
                }
                delta = base - jackpot.balance
                if delta:
                    operation = uuid4()
                    for account, kind, amount, suffix in (
                        (fund, LedgerAccountKind.KASPER_FUND, -delta, "fund"),
                        (jackpot, LedgerAccountKind.JACKPOT, delta, "jp"),
                    ):
                        movements.move(
                            account,
                            kind,
                            amount,
                            key=f"{self.step}:{lottery.id}:{suffix}",
                            operation=operation,
                            lottery=lottery.id,
                            step=self.step,
                        )
                jackpot.base_amount = base
                lottery.ticket_price = price
                lottery.ruleset_code = rule.code
                lottery.max_tickets_per_purchase = min(
                    lottery.max_tickets_per_purchase, self.per_draw_limit
                )
                lottery.max_tickets_per_user_per_draw = self.per_draw_limit
                movements.audit(
                    owner_id,
                    "lottery_economy",
                    lottery.id,
                    old,
                    {
                        "economy_step": self.step,
                        "price": price,
                        "rules": rule.code,
                        "base": base,
                        "jackpot": jackpot.balance,
                        "per_purchase": lottery.max_tickets_per_purchase,
                        "per_draw": self.per_draw_limit,
                        "jackpot_share_cas": rule.jackpot_contribution(price),
                        "burned_cas": price - rule.jackpot_contribution(price),
                    },
                )
            result = {
                "epoch": control.epoch,
                "lotteries": [term[0] for term in self.terms],
            }
            control.applied_steps = {**control.applied_steps, self.step: result}
            await self.session.flush()
            return result
