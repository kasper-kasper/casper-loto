"""Player-owned reusable lottery number combinations."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.domain.lottery_rules import get_lottery_rules
from k_loto.infrastructure.database.models import FavoriteCombination, Lottery, User


@dataclass(frozen=True, slots=True)
class FavoriteNumbers:
    id: UUID
    numbers: tuple[int, ...]


def validate_favorite_numbers(
    numbers: list[int] | tuple[int, ...], *, numbers_to_pick: int, max_number: int
) -> tuple[int, ...]:
    normalized = tuple(sorted(numbers))
    if len(normalized) != numbers_to_pick or len(set(normalized)) != numbers_to_pick:
        raise ValueError(f"Нужно выбрать ровно {numbers_to_pick} разных чисел.")
    if normalized[0] < 1 or normalized[-1] > max_number:
        raise ValueError(f"Числа должны быть от 1 до {max_number}.")
    return normalized


class FavoriteCombinationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_lottery(
        self,
        *,
        user_id: UUID,
        lottery_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[FavoriteNumbers, ...]:
        if limit < 1 or offset < 0:
            raise ValueError("Favorite page limit and offset are invalid.")
        rows = (
            await self._session.scalars(
                select(FavoriteCombination)
                .where(
                    FavoriteCombination.user_id == user_id,
                    FavoriteCombination.lottery_id == lottery_id,
                )
                .order_by(FavoriteCombination.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return tuple(FavoriteNumbers(row.id, tuple(row.numbers)) for row in rows)

    async def save(
        self, *, user_id: UUID, lottery_id: UUID, numbers: tuple[int, ...]
    ) -> tuple[FavoriteNumbers, bool]:
        async with self._session.begin():
            user = await self._session.scalar(
                select(User)
                .where(User.id == user_id, User.is_active.is_(True))
                .with_for_update()
            )
            lottery = await self._session.scalar(
                select(Lottery).where(
                    Lottery.id == lottery_id, Lottery.is_active.is_(True)
                )
            )
            if user is None or lottery is None:
                raise LookupError("Игрок или лотерея больше недоступны.")
            normalized = get_lottery_rules(lottery.ruleset_code).validate_combination(
                numbers
            )
            existing = await self._session.scalar(
                select(FavoriteCombination).where(
                    FavoriteCombination.user_id == user_id,
                    FavoriteCombination.lottery_id == lottery_id,
                    FavoriteCombination.numbers == list(normalized),
                )
            )
            if existing is not None:
                return FavoriteNumbers(existing.id, tuple(existing.numbers)), False
            favorite = FavoriteCombination(
                id=uuid4(),
                user_id=user_id,
                lottery_id=lottery_id,
                numbers=list(normalized),
            )
            self._session.add(favorite)
        return FavoriteNumbers(favorite.id, normalized), True

    async def save_for_code(
        self, *, user_id: UUID, lottery_code: str, numbers: tuple[int, ...]
    ) -> tuple[FavoriteNumbers, bool]:
        """Save atomically without a route-level query opening another transaction."""
        async with self._session.begin():
            user = await self._session.scalar(
                select(User)
                .where(User.id == user_id, User.is_active.is_(True))
                .with_for_update()
            )
            lottery = await self._session.scalar(
                select(Lottery).where(
                    Lottery.code == lottery_code, Lottery.is_active.is_(True)
                )
            )
            if user is None or lottery is None:
                raise LookupError("Игрок или лотерея больше недоступны.")
            normalized = get_lottery_rules(lottery.ruleset_code).validate_combination(
                numbers
            )
            existing = await self._session.scalar(
                select(FavoriteCombination).where(
                    FavoriteCombination.user_id == user_id,
                    FavoriteCombination.lottery_id == lottery.id,
                    FavoriteCombination.numbers == list(normalized),
                )
            )
            if existing is not None:
                return FavoriteNumbers(existing.id, tuple(existing.numbers)), False
            favorite = FavoriteCombination(
                id=uuid4(),
                user_id=user_id,
                lottery_id=lottery.id,
                numbers=list(normalized),
            )
            self._session.add(favorite)
        return FavoriteNumbers(favorite.id, normalized), True

    async def get(
        self, *, favorite_id: UUID, user_id: UUID, lottery_id: UUID
    ) -> FavoriteNumbers:
        row = await self._session.scalar(
            select(FavoriteCombination).where(
                FavoriteCombination.id == favorite_id,
                FavoriteCombination.user_id == user_id,
                FavoriteCombination.lottery_id == lottery_id,
            )
        )
        if row is None:
            raise LookupError("Любимая комбинация не найдена.")
        return FavoriteNumbers(row.id, tuple(row.numbers))

    async def delete(
        self, *, favorite_id: UUID, user_id: UUID, lottery_id: UUID
    ) -> bool:
        async with self._session.begin():
            result = await self._session.execute(
                delete(FavoriteCombination)
                .where(
                    FavoriteCombination.id == favorite_id,
                    FavoriteCombination.user_id == user_id,
                    FavoriteCombination.lottery_id == lottery_id,
                )
                .returning(FavoriteCombination.id)
            )
        return result.scalar_one_or_none() is not None

    async def delete_for_code(
        self, *, favorite_id: UUID, user_id: UUID, lottery_code: str
    ) -> bool:
        async with self._session.begin():
            lottery_id = await self._session.scalar(
                select(Lottery.id).where(
                    Lottery.code == lottery_code, Lottery.is_active.is_(True)
                )
            )
            if lottery_id is None:
                raise LookupError("Лотерея больше недоступна.")
            result = await self._session.execute(
                delete(FavoriteCombination)
                .where(
                    FavoriteCombination.id == favorite_id,
                    FavoriteCombination.user_id == user_id,
                    FavoriteCombination.lottery_id == lottery_id,
                )
                .returning(FavoriteCombination.id)
            )
        return result.scalar_one_or_none() is not None
