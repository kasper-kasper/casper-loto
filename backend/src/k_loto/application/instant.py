"""Atomic Kasper LIVE purchase and immediate settlement."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.economy import require_open
from k_loto.application.ports import SecureNumberGenerator
from k_loto.application.purchase_guard import guard_attempt
from k_loto.application.weekly import KASPER_FUND_ID, _ledger_entry
from k_loto.domain.enums import LedgerAccountKind, TransactionType
from k_loto.domain.errors import ConfigurationError, InsufficientBalance, InvalidTicket
from k_loto.domain.instant import instant_rules, instant_versions
from k_loto.domain.weekly import SystemRandomNumberGenerator
from k_loto.infrastructure.database.models import (
    Balance,
    InstantTicket,
    KasperFundAccount,
    LedgerTransaction,
)

ALLOWED_QUANTITIES = (1, 3)


@dataclass(frozen=True, slots=True)
class InstantTicketResult:
    id: UUID
    public_number: int
    symbols: tuple[int, ...]
    prize_amount: int


@dataclass(frozen=True, slots=True)
class InstantPurchaseResult:
    operation_id: UUID
    tickets: tuple[InstantTicketResult, ...]
    total_cost: int
    total_prize: int
    balance_after: int
    already_processed: bool = False


@dataclass(frozen=True, slots=True)
class InstantSummary:
    ticket_count: int
    winning_tickets: int
    losing_tickets: int
    result: int


class InstantTicketQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def history(
        self, user_id: UUID, *, limit: int = 30, game_code: str = "kasper-live"
    ) -> tuple[InstantTicketResult, ...]:
        rows = (
            await self._session.scalars(
                select(InstantTicket)
                .where(
                    InstantTicket.user_id == user_id,
                    InstantTicket.odds_version.in_(instant_versions(game_code)),
                )
                .order_by(
                    InstantTicket.purchased_at.desc(),
                    InstantTicket.public_number.desc(),
                )
                .limit(limit)
            )
        ).all()
        return tuple(
            InstantTicketResult(
                item.id,
                item.public_number,
                tuple(item.symbols),
                item.prize_amount,
            )
            for item in rows
        )

    async def summary(self, game_code: str = "kasper-live") -> InstantSummary:
        row = (
            await self._session.execute(
                select(
                    func.count(InstantTicket.id),
                    func.count(InstantTicket.id).filter(InstantTicket.prize_amount > 0),
                    func.count(InstantTicket.id).filter(
                        InstantTicket.prize_amount == 0
                    ),
                    func.coalesce(func.sum(InstantTicket.purchase_price), 0)
                    - func.coalesce(func.sum(InstantTicket.prize_amount), 0),
                ).where(InstantTicket.odds_version.in_(instant_versions(game_code)))
            )
        ).one()
        return InstantSummary(*(int(value) for value in row))


class InstantTicketPurchaseService:
    def __init__(
        self,
        session: AsyncSession,
        number_generator: SecureNumberGenerator | None = None,
        *,
        game_code: str = "kasper-live",
    ) -> None:
        self._session = session
        self._rules = instant_rules(game_code)
        self._number_generator = number_generator or SystemRandomNumberGenerator()

    async def _existing_result(
        self, ledger: LedgerTransaction
    ) -> InstantPurchaseResult:
        ids = [UUID(value) for value in ledger.details["ticket_ids"]]
        rows = (
            await self._session.scalars(
                select(InstantTicket).where(InstantTicket.id.in_(ids))
            )
        ).all()
        by_id = {item.id: item for item in rows}
        tickets = tuple(
            InstantTicketResult(
                item.id,
                item.public_number,
                tuple(item.symbols),
                item.prize_amount,
            )
            for item_id in ids
            if (item := by_id.get(item_id)) is not None
        )
        if len(tickets) != len(ids):
            raise ConfigurationError("Stored Kasper LIVE purchase is incomplete.")
        return InstantPurchaseResult(
            operation_id=ledger.operation_id,
            tickets=tickets,
            total_cost=-ledger.amount,
            total_prize=sum(item.prize_amount for item in tickets),
            balance_after=int(ledger.details["final_balance"]),
            already_processed=True,
        )

    async def purchase(
        self,
        *,
        user_id: UUID,
        quantity: int,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> InstantPurchaseResult:
        if quantity not in ALLOWED_QUANTITIES:
            raise InvalidTicket("Kasper LIVE accepts exactly 1 or 3 tickets.")
        if not idempotency_key or len(idempotency_key) > 100:
            raise ValueError("idempotency_key must contain 1 to 100 characters.")

        timestamp = now or datetime.now(UTC)
        namespace = (
            "instant"
            if self._rules.code == "kasper-live"
            else f"instant-{self._rules.code}"
        )
        user_key = f"{namespace}:{idempotency_key}:user:purchase"
        async with self._session.begin():
            await require_open(self._session)
            await guard_attempt(
                self._session, user_id, idempotency_key, self._rules.code
            )
            existing = await self._session.scalar(
                select(LedgerTransaction).where(
                    LedgerTransaction.idempotency_key == user_key
                )
            )
            if existing is not None:
                if (
                    existing.user_id != user_id
                    or existing.details.get("ticket_count") != quantity
                ):
                    raise InvalidTicket("Purchase key belongs to another request.")
                return await self._existing_result(existing)

            fund = await self._session.scalar(
                select(KasperFundAccount)
                .where(KasperFundAccount.id == KASPER_FUND_ID)
                .with_for_update()
            )
            balance = await self._session.scalar(
                select(Balance).where(Balance.user_id == user_id).with_for_update()
            )
            if balance is None or fund is None:
                raise ConfigurationError("Kasper LIVE accounts are not configured.")

            existing = await self._session.scalar(
                select(LedgerTransaction).where(
                    LedgerTransaction.idempotency_key == user_key
                )
            )
            if existing is not None:
                if (
                    existing.user_id != user_id
                    or existing.details.get("ticket_count") != quantity
                ):
                    raise InvalidTicket("Purchase key belongs to another request.")
                return await self._existing_result(existing)

            total_cost = quantity * self._rules.price
            if balance.amount < total_cost:
                raise InsufficientBalance("Insufficient CAS balance.")

            # Solvency must never select which random outcomes can commit.
            # The fund row remains locked through payment of the entire batch.
            maximum_prize = max(band.prize for band in self._rules.bands)
            if fund.balance < quantity * maximum_prize:
                raise ConfigurationError(
                    "Kasper fund cannot cover every possible prize."
                )

            prizes = tuple(
                self._rules.prize(self._number_generator.draw_sequence(1, 10_000, 1)[0])
                for _ in range(quantity)
            )
            symbols = tuple(self._rules.symbols(prize) for prize in prizes)
            total_prize = sum(prizes)
            if fund.balance < total_prize:
                raise ConfigurationError("Kasper fund cannot cover this prize.")

            operation_id = uuid4()
            tickets = [
                InstantTicket(
                    id=uuid4(),
                    user_id=user_id,
                    symbols=list(ticket_symbols),
                    purchase_price=self._rules.price,
                    prize_amount=prize,
                    odds_version=self._rules.version,
                    purchased_at=timestamp,
                    settled_at=timestamp,
                )
                for ticket_symbols, prize in zip(symbols, prizes, strict=True)
            ]
            self._session.add_all(tickets)
            await self._session.flush()

            balance_before = balance.amount
            fund_before = fund.balance
            balance_after_purchase = balance_before - total_cost
            final_balance = balance_after_purchase + total_prize
            final_fund = fund_before - total_prize
            balance.amount = final_balance
            balance.version += 1
            if total_prize:
                fund.balance = final_fund
                fund.version += 1

            ticket_ids = [str(item.id) for item in tickets]
            details = {
                "game": self._rules.code,
                "ticket_ids": ticket_ids,
                "ticket_count": quantity,
                "prizes": list(prizes),
                "total_prize": total_prize,
                "odds_version": self._rules.version,
                "final_balance": final_balance,
            }
            entries = [
                _ledger_entry(
                    operation_id=operation_id,
                    idempotency_key=user_key,
                    account_kind=LedgerAccountKind.USER_BALANCE,
                    account_id=user_id,
                    transaction_type=TransactionType.TICKET_PURCHASE,
                    before=balance_before,
                    after=balance_after_purchase,
                    user_id=user_id,
                    details=details,
                ),
            ]
            if total_prize:
                entries.extend(
                    (
                        _ledger_entry(
                            operation_id=operation_id,
                            idempotency_key=f"{namespace}:{idempotency_key}:fund:prize",
                            account_kind=LedgerAccountKind.KASPER_FUND,
                            account_id=fund.id,
                            transaction_type=TransactionType.PRIZE_PAYOUT,
                            before=fund_before,
                            after=final_fund,
                            user_id=user_id,
                            details=details,
                        ),
                        _ledger_entry(
                            operation_id=operation_id,
                            idempotency_key=f"{namespace}:{idempotency_key}:user:prize",
                            account_kind=LedgerAccountKind.USER_BALANCE,
                            account_id=user_id,
                            transaction_type=TransactionType.PRIZE_PAYOUT,
                            before=balance_after_purchase,
                            after=final_balance,
                            user_id=user_id,
                            details=details,
                        ),
                    )
                )
            self._session.add_all(entries)

        return InstantPurchaseResult(
            operation_id=operation_id,
            tickets=tuple(
                InstantTicketResult(
                    item.id,
                    item.public_number,
                    tuple(item.symbols),
                    item.prize_amount,
                )
                for item in tickets
            ),
            total_cost=total_cost,
            total_prize=total_prize,
            balance_after=final_balance,
        )
