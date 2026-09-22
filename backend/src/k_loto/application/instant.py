"""Atomic Kasper LIVE purchase and immediate settlement."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.ports import SecureNumberGenerator
from k_loto.application.weekly import KASPER_FUND_ID, _ledger_entry
from k_loto.domain.enums import LedgerAccountKind, TransactionType
from k_loto.domain.errors import ConfigurationError, InsufficientBalance, InvalidTicket
from k_loto.domain.instant import (
    ODDS_VERSION,
    SYMBOL_COUNT,
    SYMBOL_VARIANTS,
    TICKET_PRICE,
    prize_for_roll,
)
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
        self, user_id: UUID, *, limit: int = 30
    ) -> tuple[InstantTicketResult, ...]:
        rows = (
            await self._session.scalars(
                select(InstantTicket)
                .where(InstantTicket.user_id == user_id)
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

    async def summary(self) -> InstantSummary:
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
                )
            )
        ).one()
        return InstantSummary(*(int(value) for value in row))


class InstantTicketPurchaseService:
    def __init__(
        self,
        session: AsyncSession,
        number_generator: SecureNumberGenerator | None = None,
    ) -> None:
        self._session = session
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
        user_key = f"instant:{idempotency_key}:user:purchase"
        async with self._session.begin():
            existing = await self._session.scalar(
                select(LedgerTransaction).where(
                    LedgerTransaction.idempotency_key == user_key
                )
            )
            if existing is not None:
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
                return await self._existing_result(existing)

            total_cost = quantity * TICKET_PRICE
            if balance.amount < total_cost:
                raise InsufficientBalance("Insufficient CAS balance.")

            prizes = tuple(
                prize_for_roll(self._number_generator.draw_sequence(1, 10_000, 1)[0])
                for _ in range(quantity)
            )
            symbols = tuple(
                self._number_generator.draw_sequence(1, SYMBOL_VARIANTS, SYMBOL_COUNT)
                for _ in range(quantity)
            )
            total_prize = sum(prizes)
            if fund.balance < total_prize:
                raise ConfigurationError("Kasper fund cannot cover this prize.")

            operation_id = uuid4()
            tickets = [
                InstantTicket(
                    id=uuid4(),
                    user_id=user_id,
                    symbols=list(ticket_symbols),
                    purchase_price=TICKET_PRICE,
                    prize_amount=prize,
                    odds_version=ODDS_VERSION,
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
                "game": "kasper-live",
                "ticket_ids": ticket_ids,
                "ticket_count": quantity,
                "prizes": list(prizes),
                "total_prize": total_prize,
                "odds_version": ODDS_VERSION,
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
                            idempotency_key=f"instant:{idempotency_key}:fund:prize",
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
                            idempotency_key=f"instant:{idempotency_key}:user:prize",
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
