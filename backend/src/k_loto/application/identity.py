"""Telegram identity binding without business rules in bot handlers."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import String, cast, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.welcome import WelcomeGrantService
from k_loto.infrastructure.database.models import (
    Balance,
    LedgerTransaction,
    User,
    UserNotificationPreference,
)


@dataclass(frozen=True, slots=True)
class UserProfile:
    id: UUID
    display_name: str
    balance: int


class TelegramIdentityService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bind(
        self,
        *,
        telegram_id: int,
        username: str | None,
        display_name: str,
    ) -> UserProfile:
        if telegram_id <= 0:
            raise ValueError("telegram_id must be positive.")
        clean_name = display_name.strip() or "Casper Loto Player"
        clean_username = username.strip() if username else None
        new_user_id = uuid4()

        async with self._session.begin():
            # Normal reads must not take the balance lock used by purchases.
            # Only fully initialized accounts with the immutable v2 grant receipt
            # can use this path; new/legacy accounts retain the locked setup below.
            ready = (
                await self._session.execute(
                    select(User, Balance.amount)
                    .join(Balance, Balance.user_id == User.id)
                    .join(
                        UserNotificationPreference,
                        UserNotificationPreference.user_id == User.id,
                    )
                    .join(
                        LedgerTransaction,
                        LedgerTransaction.idempotency_key
                        == func.concat(
                            "welcome-grant:user:", cast(User.id, String), ":v2"
                        ),
                    )
                    .where(User.telegram_id == telegram_id)
                )
            ).first()
            if ready is not None:
                user, current_balance = ready
                if user.username != clean_username:
                    user.username = clean_username
                if user.display_name != clean_name:
                    user.display_name = clean_name
                return UserProfile(user.id, clean_name, current_balance)
            user_id = await self._session.scalar(
                insert(User)
                .values(
                    id=new_user_id,
                    telegram_id=telegram_id,
                    username=clean_username,
                    display_name=clean_name,
                    is_active=True,
                    is_admin=False,
                )
                .on_conflict_do_update(
                    index_elements=[User.telegram_id],
                    set_={"username": clean_username, "display_name": clean_name},
                )
                .returning(User.id)
            )
            if user_id is None:
                raise RuntimeError("Telegram user binding returned no identity.")
            await self._session.execute(
                insert(Balance)
                .values(user_id=user_id, amount=0, version=1)
                .on_conflict_do_nothing(index_elements=[Balance.user_id])
            )
            await self._session.execute(
                insert(UserNotificationPreference)
                .values(user_id=user_id)
                .on_conflict_do_nothing(
                    index_elements=[UserNotificationPreference.user_id]
                )
            )
            balance = await self._session.scalar(
                select(Balance.amount).where(Balance.user_id == user_id)
            )
            if balance is None:
                raise RuntimeError("Telegram user balance was not created.")
            grant = await WelcomeGrantService.ensure_in_transaction(
                self._session, user_id
            )

        return UserProfile(user_id, clean_name, grant.balance)
