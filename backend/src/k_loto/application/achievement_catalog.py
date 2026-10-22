"""Local catalog management and explicit launch; never part of a player request."""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.achievement_results import instant_result, ticket_result
from k_loto.application.achievements import (
    REWARD_ADAPTERS,
    Catalog,
    enqueue,
    worker_lock,
)
from k_loto.core.config import get_settings
from k_loto.domain.achievements import RARITIES, RewardSpec, Rule
from k_loto.domain.enums import TicketStatus
from k_loto.domain.instant import INSTANT_GAMES
from k_loto.infrastructure.database.achievement_models import (
    AchievementAward,
    AchievementDefinition,
    AchievementEvent,
    AchievementPlayer,
    AchievementRuntime,
)
from k_loto.infrastructure.database.models import Draw, InstantTicket, Lottery, Ticket


class CatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    code: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]{0,79}$")
    version: int = Field(ge=1)
    rarity: Literal["common", "uncommon", "rare", "epic", "legendary"]
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(max_length=512)
    flavor: str | None = Field(default=None, max_length=512)
    secret: bool = False
    active: bool = False
    visible: bool = True
    sort_order: int = 0
    icon: str | None = Field(default=None, max_length=512)
    condition: Rule
    rewards: list[RewardSpec] = Field(default_factory=list, max_length=16)
    reward_pending: bool = False

    @model_validator(mode="after")
    def pending_has_no_amount(self) -> "CatalogEntry":
        if self.reward_pending and self.rewards:
            raise ValueError("Unapproved rewards cannot contain payable amounts")
        return self


def require_local(session: AsyncSession) -> None:
    bind = session.get_bind()
    if (
        get_settings().app_env == "production"
        or bind.engine.url.host not in {"localhost", "127.0.0.1", "::1"}
        or not (bind.engine.url.database or "").startswith("k_loto_achievement_")
    ):
        raise ValueError(
            "Foundation management requires a local k_loto_achievement_* database"
        )


async def launch_local(session: AsyncSession) -> datetime:
    require_local(session)
    return await _start_tracking(session)


async def _start_tracking(session: AsyncSession) -> datetime:
    """Atomic launch boundary shared by guarded local and production commands."""
    if not await worker_lock(session):
        raise ValueError("Achievement worker is busy; retry management later")
    runtime = await session.scalar(
        select(AchievementRuntime).where(AchievementRuntime.id == 1).with_for_update()
    )
    if runtime is None or runtime.started_at is not None:
        raise ValueError("Launch is once-only; progress is never reset")
    # A one-time write barrier excludes in-flight source operations.
    await session.execute(text("SET LOCAL lock_timeout = '2s'"))
    await session.execute(
        text(
            "LOCK TABLE tickets, instant_tickets, draws, ledger_transactions, "
            "balances IN SHARE ROW EXCLUSIVE MODE NOWAIT"
        )
    )
    now = await session.scalar(select(func_clock()))
    assert isinstance(now, datetime)
    await session.execute(
        text("""
        INSERT INTO achievement_players(user_id,metrics)
        SELECT user_id,jsonb_build_object('baseline_balance',amount,
            'current_balance',amount,'max_balance',amount)
        FROM balances ON CONFLICT(user_id) DO NOTHING
    """)
    )
    runtime.started_at, runtime.enabled = now, True
    for user_id in (await session.scalars(select(AchievementPlayer.user_id))).all():
        await enqueue(
            session, f"baseline:{user_id}", "baseline", {}, user_id, occurred_at=now
        )
    return now


def func_clock() -> Any:
    from sqlalchemy import func

    return func.clock_timestamp()


async def import_catalog(session: AsyncSession, entries: list[CatalogEntry]) -> None:
    require_local(session)
    await _import_catalog(session, entries)


async def _import_catalog(session: AsyncSession, entries: list[CatalogEntry]) -> None:
    """Validated import; callers must enforce their management environment."""
    if len({entry.code for entry in entries}) != len(entries):
        raise ValueError("Duplicate achievement code")
    for entry in entries:
        if entry.rarity not in RARITIES:
            raise ValueError("Unknown rarity")
        if entry.active and any(
            reward.type not in REWARD_ADAPTERS and not reward.planned
            for reward in entry.rewards
        ):
            raise ValueError("Cannot activate an unavailable reward adapter")
        from k_loto.application.collection import collection_catalog

        if any(
            r.type == "cosmetic" and r.item not in collection_catalog()
            for r in entry.rewards
        ):
            raise ValueError("Cosmetic reward item is unavailable")
    known_lotteries = set((await session.scalars(select(Lottery.code))).all()) | set(
        INSTANT_GAMES
    )
    if any(
        c.lottery and c.lottery not in known_lotteries
        for entry in entries
        for c in entry.condition.conditions
    ):
        raise ValueError("Unknown lottery in achievement condition")
    if not await worker_lock(session):
        raise ValueError("Achievement worker is busy; retry management later")
    runtime = await session.get(AchievementRuntime, 1)
    assert runtime is not None
    old_catalog = await Catalog.load(session)
    now = datetime.now(UTC)
    for entry in entries:
        previous = old_catalog.definitions.get(entry.code)
        old_data = (
            {k: getattr(previous, k) for k in entry.model_dump()} if previous else {}
        )
        if previous:
            old_data["condition"] = Rule.model_validate(previous.condition).model_dump()
        if (
            previous
            and entry.model_dump() != old_data
            and entry.version <= previous.version
        ):
            raise ValueError("A changed definition requires a higher version")
        data = entry.model_dump()
        if previous:
            for key, value in data.items():
                setattr(previous, key, value)
            if entry.active and previous.activated_at is None:
                previous.activated_at = now
        else:
            session.add(
                AchievementDefinition(
                    **data, activated_at=now if entry.active else None
                )
            )
    await session.flush()
    catalog = await Catalog.load(session)
    # A fixed collection must reference existing definitions and cannot depend on
    # itself, directly or through another collection.
    graph = {
        code: {
            required for c in rule.conditions for required in c.achievement_codes or []
        }
        for code, rule in catalog.rules.items()
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(code: str) -> None:
        if code not in graph or code in visiting:
            raise ValueError("Unknown or cyclic achievement collection dependency")
        if code in visited:
            return
        visiting.add(code)
        for required in graph[code]:
            visit(required)
        visiting.remove(code)
        visited.add(code)

    for code in graph:
        visit(code)
    set_conditions = {
        c.key: c
        for rule in catalog.rules.values()
        for c in rule.conditions
        if c.metric == "earned_set"
    }
    old_set_keys = {
        c.key
        for rule in old_catalog.rules.values()
        for c in rule.conditions
        if c.metric == "earned_set"
    }
    new_sets = {key: c for key, c in set_conditions.items() if key not in old_set_keys}
    if new_sets:
        # Management-time initialization only; never run by profile reads.
        for player in (await session.scalars(select(AchievementPlayer))).all():
            earned = set(
                await session.scalars(
                    select(AchievementAward.code).where(
                        AchievementAward.user_id == player.user_id
                    )
                )
            )
            player.metrics = {
                **player.metrics,
                **{
                    key: len(earned.intersection(c.achievement_codes or []))
                    for key, c in new_sets.items()
                },
            }
    from k_loto.application.achievement_progress import EXTENDED_METRICS, RARE_METRICS

    if EXTENDED_METRICS.intersection(catalog.watchers):
        from k_loto.application.achievement_backfill import initialize_extended_progress

        needs_rare = bool(RARE_METRICS.intersection(catalog.watchers)) or any(
            c.metric == "consecutive_winning_draws" and c.target > 2
            for rule in catalog.rules.values()
            for c in rule.conditions
        )
        needs_epic = any(
            c.metric == "consecutive_winning_draws" and c.target > 3
            for rule in catalog.rules.values()
            for c in rule.conditions
        )
        await initialize_extended_progress(
            session, runtime, revision=3 if needs_epic else 2 if needs_rare else 1
        )
    new_filters = {
        key: c for key, c in catalog.filters.items() if key not in old_catalog.filters
    }
    if runtime.started_at and new_filters:
        # New thresholds recover only post-launch facts already projected. This
        # offline management operation never awards or touches business history.
        await rebuild_filters(session, new_filters)
    runtime.catalog_revision += 1
    if runtime.enabled:
        for user_id in (await session.scalars(select(AchievementPlayer.user_id))).all():
            await enqueue(
                session,
                f"catalog:{runtime.catalog_revision}:{user_id}",
                "evaluate",
                {},
                user_id,
            )


async def rebuild_filters(session: AsyncSession, filters: dict[str, Any]) -> None:
    runtime = await session.get(AchievementRuntime, 1)
    assert runtime is not None and runtime.started_at is not None
    await session.execute(
        text(
            "UPDATE achievement_players SET metrics=metrics-CAST(:keys AS text[]) "
            "WHERE metrics ?| CAST(:keys AS text[])"
        ),
        {"keys": list(filters)},
    )
    last_id = 0
    while True:
        events = list(
            (
                await session.scalars(
                    select(AchievementEvent)
                    .where(
                        AchievementEvent.id > last_id,
                        AchievementEvent.kind.in_(["draw", "instant"]),
                    )
                    .order_by(AchievementEvent.id)
                    .limit(100)
                )
            ).all()
        )
        if not events:
            break
        for event in events:
            results: list[tuple[UUID, dict[str, Any]]] = []
            if event.kind == "instant" and event.processed_at:
                ticket = await session.get(InstantTicket, UUID(event.payload["ticket"]))
                assert ticket is not None
                results.append((ticket.user_id, instant_result(ticket)))
                await add_filter_results(session, filters, results)
            elif event.kind == "draw" and event.cursor:
                draw = await session.get(Draw, UUID(event.payload["draw"]))
                assert draw is not None
                lottery = await session.get(Lottery, draw.lottery_id)
                assert lottery is not None
                cursor: UUID | None = None
                while True:
                    from sqlalchemy import and_, or_

                    query = select(Ticket).where(
                        Ticket.status == TicketStatus.SETTLED,
                        Ticket.purchased_at >= runtime.started_at,
                        Ticket.purchase_price > 0,
                        Ticket.id <= UUID(event.cursor),
                        or_(
                            and_(
                                Ticket.draw_id == draw.id,
                                Ticket.second_draw_id.is_(None),
                            ),
                            Ticket.second_draw_id == draw.id,
                        ),
                    )
                    if cursor:
                        query = query.where(Ticket.id > cursor)
                    tickets = list(
                        (
                            await session.scalars(query.order_by(Ticket.id).limit(100))
                        ).all()
                    )
                    if not tickets:
                        break
                    await add_filter_results(
                        session,
                        filters,
                        [(t.user_id, ticket_result(t, draw, lottery)) for t in tickets],
                    )
                    cursor = tickets[-1].id
            last_id = event.id


async def add_filter_results(
    session: AsyncSession,
    filters: dict[str, Any],
    results: list[tuple[UUID, dict[str, Any]]],
) -> None:
    changes: dict[UUID, dict[str, int]] = {}
    for user_id, result in results:
        metrics = changes.setdefault(user_id, {})
        for key, condition in filters.items():
            if condition.matches_result(result):
                metrics[key] = metrics.get(key, 0) + 1
    for user_id, changeset in changes.items():
        player = await session.get(AchievementPlayer, user_id)
        assert player is not None
        player.metrics = {
            **player.metrics,
            **{
                key: player.metrics.get(key, 0) + value
                for key, value in changeset.items()
            },
        }
    await session.flush()
