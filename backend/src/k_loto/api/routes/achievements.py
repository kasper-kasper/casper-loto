"""Authenticated read API; projection and rewards never run in HTTP reads."""

from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import cast, select, update
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.api.dependencies import (
    CurrentMiniAppUser,
    get_current_miniapp_user,
    get_db_session,
)
from k_loto.application.achievements import (
    AchievementProjection,
    Catalog,
    record_activity,
)
from k_loto.domain.achievements import RARITIES, Rule
from k_loto.infrastructure.database.achievement_models import (
    AchievementAward,
    AchievementPlayer,
    AchievementRuntime,
)
from k_loto.infrastructure.database.models import (
    UserNotification,
    UserNotificationPreference,
)

router = APIRouter(prefix="/api/v1/miniapp/achievements", tags=["achievements"])
Session = Annotated[AsyncSession, Depends(get_db_session)]
Player = Annotated[CurrentMiniAppUser, Depends(get_current_miniapp_user)]


@router.post("/activity", status_code=204)
async def activity(user: Player, session: Session) -> Response:
    async with session.begin():
        await record_activity(session, user.id, datetime.now(UTC))
    return Response(status_code=204)


@router.get("")
async def achievements(
    user: Player,
    session: Session,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    category: Literal["common", "uncommon", "rare", "epic", "legendary", "secret"]
    | None = None,
    status: Literal["all", "earned", "locked"] = "all",
    summary: bool = False,
    focus: Annotated[str | None, Query(max_length=80)] = None,
) -> dict[str, Any]:
    response.headers["Cache-Control"] = "private, no-store"
    runtime = await session.get(AchievementRuntime, 1)
    if runtime is None or not runtime.enabled:
        return {
            "enabled": False,
            "total": 0,
            "earned": 0,
            "earned_by_category": dict.fromkeys(RARITIES, 0),
            "items": [],
        }
    catalog = await Catalog.cached(session, runtime.catalog_revision)
    awards = {
        a.code: a
        for a in (
            await session.scalars(
                select(AchievementAward).where(AchievementAward.user_id == user.id)
            )
        ).all()
    }
    player = await session.get(AchievementPlayer, user.id)
    definitions = sorted(
        (
            d
            for d in catalog.definitions.values()
            if d.visible and (d.active or d.code in awards)
        ),
        key=lambda d: (d.sort_order, RARITIES.index(d.rarity), d.code),
    )
    visible_codes = {d.code for d in definitions}
    selected_category: str | None = category
    focused_definition = next((d for d in definitions if d.code == focus), None)
    if focused_definition is not None and not summary:
        selected_category = (
            "secret"
            if selected_category == "secret" and focused_definition.secret
            else focused_definition.rarity
        )
        status = "all"
    all_awards = awards
    awards = {code: award for code, award in awards.items() if code in visible_codes}
    by_category = {
        rarity: sum(a.rarity == rarity for a in awards.values()) for rarity in RARITIES
    }
    totals = {
        rarity: sum(d.rarity == rarity for d in definitions) for rarity in RARITIES
    }
    totals["secret"] = sum(d.secret for d in definitions)
    by_category["secret"] = sum(d.secret and d.code in awards for d in definitions)
    total = len(definitions)
    if summary:
        definitions = sorted(
            (d for d in definitions if d.code in awards),
            key=lambda d: (awards[d.code].earned_at, d.code),
            reverse=True,
        )[:3]
    else:
        definitions = [
            d
            for d in definitions
            if (
                selected_category is None
                or (
                    d.secret
                    if selected_category == "secret"
                    else d.rarity == selected_category
                )
            )
            and (status == "all" or (d.code in awards) == (status == "earned"))
        ]
    projection = AchievementProjection(session, catalog, award=False)
    projection.earned_times[user.id] = sorted(
        award.earned_at for award in all_awards.values()
    )
    now = datetime.now(UTC)
    items = []
    for definition in definitions:
        award = awards.get(definition.code)
        if definition.secret and award is None:
            items.append(
                {
                    "code": definition.code,
                    "rarity": definition.rarity,
                    "secret": True,
                    "status": "locked",
                }
            )
            continue
        snapshot = (
            award.snapshot
            if award
            else {
                name: getattr(definition, name)
                for name in (
                    "title",
                    "description",
                    "flavor",
                    "rarity",
                    "icon",
                    "condition",
                    "rewards",
                    "reward_pending",
                    "secret",
                )
            }
        )
        progress = []
        if not award:
            display_player = player or AchievementPlayer(user_id=user.id, metrics={})
            for c in Rule.model_validate(snapshot["condition"]).conditions:
                progress.append(
                    {
                        "metric": c.metric,
                        "current": await projection.value(display_player, c, now),
                        "target": c.target,
                        "operator": c.op,
                    }
                )
        items.append(
            {
                "code": definition.code,
                "title": snapshot["title"],
                "description": snapshot["description"],
                "flavor": snapshot.get("flavor"),
                "rarity": snapshot["rarity"],
                "icon": snapshot["icon"],
                "secret": snapshot["secret"],
                "status": "earned" if award else "locked",
                "active": definition.active,
                "progress": progress,
                "progress_mode": Rule.model_validate(snapshot["condition"]).mode,
                "rewards": snapshot["rewards"],
                "earned_at": award.earned_at if award else None,
                "reward_status": award.reward_status if award else None,
                "reward_pending": snapshot.get("reward_pending", False),
                "sort_order": definition.sort_order,
            }
        )

    def sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
        progress = item.get("progress", [])
        ratios = [min(1, p["current"] / max(1, p["target"])) for p in progress]
        ratio = (
            (max(ratios) if item.get("progress_mode") == "any" else min(ratios))
            if ratios
            else 0
        )
        return (
            item["status"] != "earned",
            -ratio,
            catalog.definitions[item["code"]].sort_order,
            item["code"],
        )

    if not summary:
        items.sort(key=sort_key)
    filtered_total = len(items)
    return {
        "enabled": True,
        "started_at": runtime.started_at,
        "catalog_revision": runtime.catalog_revision,
        "total": total,
        "earned": len(awards),
        "earned_by_category": by_category,
        "total_by_category": totals,
        "filtered_total": filtered_total,
        "updated_at": player.updated_at if player else None,
        "featured": player.featured if player else [],
        "telegram_enabled": player.telegram_enabled if player else False,
        "items": items[offset : offset + limit],
        "focused_item": next((item for item in items if item["code"] == focus), None),
        "focused_category": selected_category
        if focused_definition is not None
        else None,
        "next_offset": offset + limit if offset + limit < filtered_total else None,
    }


@router.get("/unseen")
async def unseen(
    user: Player, session: Session, response: Response
) -> list[dict[str, Any]]:
    response.headers["Cache-Control"] = "private, no-store"
    runtime = await session.get(AchievementRuntime, 1)
    if runtime is None or not runtime.enabled:
        return []
    preference = await session.get(UserNotificationPreference, user.id)
    if preference is not None and not preference.in_app_enabled:
        return []
    pending_query = select(
        UserNotification.id, UserNotification.payload, UserNotification.created_at
    ).where(
        UserNotification.user_id == user.id,
        UserNotification.read_at.is_(None),
        UserNotification.type == "ACHIEVEMENT",
    )
    if preference is not None and preference.in_app_enabled_at is not None:
        pending_query = pending_query.where(
            UserNotification.created_at >= preference.in_app_enabled_at
        )
    pending = (
        pending_query.order_by(UserNotification.created_at, UserNotification.id)
        .limit(10)
        .subquery()
    )
    rows = (
        await session.execute(
            select(
                pending.c.id,
                AchievementAward.snapshot,
                AchievementAward.reward_status,
                AchievementAward.earned_at,
            )
            .join(
                AchievementAward,
                AchievementAward.id
                == cast(pending.c.payload["award"].astext, PGUUID(as_uuid=True)),
            )
            .where(AchievementAward.user_id == user.id)
            .order_by(pending.c.created_at, pending.c.id)
        )
    ).all()
    return [
        {
            "notification_id": row.id,
            **row.snapshot,
            "status": "earned",
            "reward_status": row.reward_status,
            "earned_at": row.earned_at,
        }
        for row in rows
    ]


class Seen(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=10)


@router.post("/seen", status_code=204)
async def seen(payload: Seen, user: Player, session: Session) -> Response:
    async with session.begin():
        await session.execute(
            update(UserNotification)
            .where(
                UserNotification.user_id == user.id,
                UserNotification.id.in_(payload.ids),
                UserNotification.type == "ACHIEVEMENT",
                UserNotification.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
    return Response(status_code=204)


class Preferences(BaseModel):
    telegram_enabled: bool


@router.put("/preferences")
async def preferences(
    payload: Preferences, user: Player, session: Session
) -> dict[str, bool]:
    async with session.begin():
        runtime = await session.get(AchievementRuntime, 1)
        if runtime is None or not runtime.enabled:
            raise HTTPException(409, "Achievements are not enabled")
        player = await AchievementProjection(session, Catalog([])).player(user.id)
        player.telegram_enabled = payload.telegram_enabled
    return {"telegram_enabled": payload.telegram_enabled}


class Featured(BaseModel):
    codes: list[str] = Field(max_length=3)


@router.get("/collection")
async def collection(
    user: Player, session: Session, response: Response
) -> dict[str, Any]:
    from k_loto.application.collection import read_collection

    response.headers["Cache-Control"] = "private, no-store"
    return await read_collection(session, user.id)


class CollectionChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    badge: str | None = Field(default=None, max_length=80)
    theme: str | None = Field(default=None, max_length=80)


@router.put("/collection")
async def collection_choice(
    payload: CollectionChoice, user: Player, session: Session
) -> dict[str, str | None]:
    from k_loto.application.collection import choose_cosmetics

    try:
        async with session.begin():
            return await choose_cosmetics(
                session, user.id, badge=payload.badge, theme=payload.theme
            )
    except ValueError as error:
        raise HTTPException(400, str(error)) from error


@router.put("/featured")
async def featured(
    payload: Featured, user: Player, session: Session
) -> dict[str, list[str]]:
    async with session.begin():
        runtime = await session.get(AchievementRuntime, 1)
        if runtime is None or not runtime.enabled:
            raise HTTPException(409, "Achievements are not enabled")
        earned = set(
            (
                await session.scalars(
                    select(AchievementAward.code).where(
                        AchievementAward.user_id == user.id
                    )
                )
            ).all()
        )
        if (
            len(set(payload.codes)) != len(payload.codes)
            or not set(payload.codes) <= earned
        ):
            raise HTTPException(422, "Only distinct owned achievements can be featured")
        player = await AchievementProjection(session, Catalog([])).player(user.id)
        player.featured = payload.codes
    return {"codes": payload.codes}
