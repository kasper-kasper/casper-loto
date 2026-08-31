"""Idempotent welcome funding through the immutable CAS ledger."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.domain.enums import LedgerAccountKind, TransactionType
from k_loto.infrastructure.database.models import Balance, LedgerTransaction

WELCOME_GRANT_CAS = 100_000_000_000


@dataclass(frozen=True, slots=True)
class WelcomeGrantResult:
    balance: int
    credited: bool


class WelcomeGrantService:
    """Credit the one-time player grant; retries never mint CAS twice."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure(self, user_id: UUID) -> WelcomeGrantResult:
        async with self._session.begin():
            return await self.ensure_in_transaction(self._session, user_id)

    @staticmethod
    async def ensure_in_transaction(
        session: AsyncSession, user_id: UUID
    ) -> WelcomeGrantResult:
        key = f"welcome-grant:user:{user_id}:v2"
        legacy_key = f"welcome-grant:user:{user_id}:v1"
        balance = await session.scalar(
            select(Balance).where(Balance.user_id == user_id).with_for_update()
        )
        if balance is None:
            raise RuntimeError("Player balance account is missing.")
        existing = await session.scalar(
            select(LedgerTransaction).where(LedgerTransaction.idempotency_key == key)
        )
        if existing is not None:
            return WelcomeGrantResult(balance.amount, False)
        legacy = await session.scalar(
            select(LedgerTransaction).where(
                LedgerTransaction.idempotency_key == legacy_key
            )
        )
        legacy_grant = legacy.amount if legacy is not None and legacy.amount > 0 else 0
        grant_amount = max(WELCOME_GRANT_CAS - legacy_grant, 0)
        before = balance.amount
        balance.amount += grant_amount
        balance.version += 1
        session.add(
            LedgerTransaction(
                id=uuid4(),
                operation_id=uuid4(),
                idempotency_key=key,
                account_kind=LedgerAccountKind.USER_BALANCE,
                account_id=user_id,
                type=TransactionType.SYSTEM_ADJUSTMENT,
                amount=grant_amount,
                balance_before=before,
                balance_after=balance.amount,
                user_id=user_id,
                details={
                    "reason": "automatic one-time player welcome grant",
                    "target_grant": WELCOME_GRANT_CAS,
                    "legacy_grant": legacy_grant,
                },
            )
        )
        return WelcomeGrantResult(balance.amount, True)
