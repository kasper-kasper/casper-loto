"""Telegram identity binding without business rules in bot handlers."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.infrastructure.database.models import Balance, User


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
        clean_name = display_name.strip() or "K-Loto Player"
        clean_username = username.strip() if username else None
        new_user_id = uuid4()

        async with self._session.begin():
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
            balance = await self._session.scalar(
                select(Balance.amount).where(Balance.user_id == user_id)
            )
            if balance is None:
                raise RuntimeError("Telegram user balance was not created.")

        return UserProfile(user_id, clean_name, balance)
