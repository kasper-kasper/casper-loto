"""Permanent cosmetic ownership and opt-in presentation, independent of balances."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.infrastructure.database.achievement_models import (
    AchievementAward,
    AchievementReward,
    CollectionPreference,
    CollectionUnlock,
)

GAME_NAMES = {
    "flash": "FLASH",
    "shadow": "CODE",
    "pulse": "PULSE",
    "khan": "6 из 36",
    "pss": "Casper Ball",
    "weekly": "Casper Grand",
    "bingo": "Casper Bingo",
    "pll": "2:22",
    "september": "3 сентября",
    "grob": "Halloween",
}


async def selected_badges(
    session: AsyncSession, user_ids: list[UUID]
) -> dict[UUID, str]:
    """One bounded projection for future rankings/public player lists."""
    if len(user_ids) > 200:
        raise ValueError("Public badge projection requires a bounded page")
    if not user_ids:
        return {}
    rows = await session.execute(
        select(CollectionPreference.user_id, CollectionPreference.active_badge).where(
            CollectionPreference.user_id.in_(user_ids),
            CollectionPreference.active_badge.is_not(None),
        )
    )
    return {row.user_id: row.active_badge for row in rows}


def collection_catalog() -> dict[str, dict[str, str]]:
    from k_loto.application.legendary_achievements import LEGENDARY_ROWS

    result = {
        f"badge:{row[0]}": dict(
            kind="badge",
            title=GAME_NAMES[row[0]],
            game=row[0],
            description=f"Легендарное достижение «{row[1]}»",
        )
        for row in LEGENDARY_ROWS
    }
    result["badge:casper-master"] = dict(
        kind="badge",
        title="Каспер, подвинься",
        game="casper-master",
        description="Все десять исходных легендарных достижений",
    )
    result["theme:gold"] = dict(
        kind="theme",
        title="Золотая",
        game="",
        description="Первое легендарное достижение",
    )
    result["theme:beyond"] = dict(
        kind="theme",
        title="За гранью",
        game="",
        description="Все десять исходных легендарных достижений",
    )
    return result


async def grant_cosmetic(
    session: AsyncSession, award: AchievementAward, part: AchievementReward
) -> None:
    item = str(part.payload["item"])
    if item not in collection_catalog():
        raise ValueError("Unknown collectible item")
    await session.execute(
        insert(CollectionUnlock)
        .values(user_id=award.user_id, item=item, award_id=award.id)
        .on_conflict_do_nothing()
    )


async def read_collection(session: AsyncSession, user_id: UUID) -> dict[str, Any]:
    owned = {
        row.item: row
        for row in await session.scalars(
            select(CollectionUnlock).where(CollectionUnlock.user_id == user_id)
        )
    }
    preferences = await session.get(CollectionPreference, user_id)
    return dict(
        active_badge=preferences.active_badge if preferences else None,
        active_theme=preferences.active_theme if preferences else None,
        items=[
            dict(
                code=code,
                **item,
                unlocked=code in owned,
                unlocked_at=owned[code].unlocked_at if code in owned else None,
            )
            for code, item in collection_catalog().items()
        ],
    )


async def choose_cosmetics(
    session: AsyncSession, user_id: UUID, *, badge: str | None, theme: str | None
) -> dict[str, str | None]:
    catalog = collection_catalog()
    for code, kind in [(badge, "badge"), (theme, "theme")]:
        if code is None:
            continue
        if code not in catalog or catalog[code]["kind"] != kind:
            raise ValueError("Unknown item or incorrect cosmetic slot")
        if await session.get(CollectionUnlock, (user_id, code)) is None:
            raise ValueError("This cosmetic item has not been unlocked")
    await session.execute(
        insert(CollectionPreference).values(user_id=user_id).on_conflict_do_nothing()
    )
    preference = await session.get(CollectionPreference, user_id, with_for_update=True)
    assert preference is not None
    preference.active_badge, preference.active_theme = badge, theme
    return dict(active_badge=badge, active_theme=theme)
