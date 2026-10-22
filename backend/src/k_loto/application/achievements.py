"""Transactional, incremental achievement projection and bounded worker."""

from bisect import bisect_left, bisect_right, insort
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4
from weakref import WeakKeyDictionary

from sqlalchemy import and_, func, or_, select, text, true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from k_loto.application.achievement_packs import deliver_pack
from k_loto.application.achievement_progress import EXTENDED_METRICS, ExtendedProgress
from k_loto.application.achievement_results import instant_result, ticket_result
from k_loto.application.collection import grant_cosmetic
from k_loto.application.weekly import _ledger_entry
from k_loto.core.config import get_settings
from k_loto.domain.achievements import (
    Condition,
    Rule,
    activity_progress,
    metric_key,
)
from k_loto.domain.enums import (
    InAppNotificationType,
    LedgerAccountKind,
    NotificationType,
    TicketStatus,
    TransactionType,
)
from k_loto.domain.errors import InsufficientBalance, NoAvailableDraw
from k_loto.domain.schedules import MOSCOW
from k_loto.infrastructure.database.achievement_models import (
    AchievementAward,
    AchievementCorrection,
    AchievementDefinition,
    AchievementEvent,
    AchievementParticipation,
    AchievementPlayer,
    AchievementReward,
    AchievementRuntime,
)
from k_loto.infrastructure.database.models import (
    Balance,
    Draw,
    InstantTicket,
    KasperFundAccount,
    Lottery,
    NotificationOutbox,
    Ticket,
    UserNotification,
)

WORKER_LOCK = 72410830
PAGE_SIZE = 100
_catalog_cache: WeakKeyDictionary[Engine, tuple[int, "Catalog"]] = WeakKeyDictionary()
EventAdapter = Callable[
    [AsyncSession, AchievementPlayer, dict[str, int], AchievementEvent],
    Awaitable[set[str]],
]
EVENT_ADAPTERS: dict[str, EventAdapter] = {}


def register_event_adapter(kind: str, adapter: EventAdapter) -> None:
    if (
        kind
        in {
            "draw",
            "reward",
            "reward_paid",
            "purchase",
            "refund",
            "wallet",
            "activity",
            "instant",
            "baseline",
            "evaluate",
            "gift_received",
        }
        or kind in EVENT_ADAPTERS
    ):
        raise ValueError("Event adapter is already registered or reserved")
    EVENT_ADAPTERS[kind] = adapter


async def worker_lock(session: AsyncSession) -> bool:
    """Coordinate processors only; gameplay never takes this advisory lock."""
    return bool(
        await session.scalar(
            text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": WORKER_LOCK}
        )
    )


class Catalog:
    def __init__(self, definitions: list[AchievementDefinition]) -> None:
        self.definitions = {d.code: d for d in definitions}
        self.rules = {d.code: Rule.model_validate(d.condition) for d in definitions}
        self.watchers: dict[str, set[str]] = defaultdict(set)
        self.filters: dict[str, Condition] = {}
        self.result_filters: dict[str, dict[str, Condition]] = defaultdict(dict)
        self.earned_dependencies: dict[str, set[str]] = defaultdict(set)
        for code, rule in self.rules.items():
            for c in rule.conditions:
                for required in c.achievement_codes or []:
                    self.earned_dependencies[required].add(c.key)
                if c.metric in {"qualifying_wins", "result_count"}:
                    self.filters[c.key] = c
                    self.result_filters[c.lottery or ""][c.key] = c
                if self.definitions[code].active:
                    self.watchers[c.key].add(code)

    @classmethod
    async def load(cls, session: AsyncSession) -> "Catalog":
        return cls(list((await session.scalars(select(AchievementDefinition))).all()))

    @classmethod
    async def cached(cls, session: AsyncSession, revision: int) -> "Catalog":
        engine = session.get_bind().engine
        cached = _catalog_cache.get(engine)
        if cached and cached[0] == revision:
            return cached[1]
        catalog = await cls.load(session)
        _catalog_cache[engine] = (revision, catalog)
        return catalog


class AchievementProjection:
    def __init__(
        self, session: AsyncSession, catalog: Catalog, *, award: bool = True
    ) -> None:
        self.session = session
        self.catalog = catalog
        self.award_enabled = award
        self.players: dict[UUID, AchievementPlayer] = {}
        self.earned: dict[UUID, set[str]] = {}
        self.earned_times: dict[UUID, list[datetime]] = {}
        self.extended = (
            ExtendedProgress(session)
            if EXTENDED_METRICS.intersection(catalog.watchers)
            else None
        )

    async def player(self, user_id: UUID) -> AchievementPlayer:
        if user_id not in self.players:
            await self.session.execute(
                insert(AchievementPlayer)
                .values(user_id=user_id)
                .on_conflict_do_nothing()
            )
            player = await self.session.get(AchievementPlayer, user_id)
            assert player is not None
            self.players[user_id] = player
        return self.players[user_id]

    async def apply(self, event: AchievementEvent) -> bool:
        """Return False while a frozen draw still has another page to process."""
        if event.kind in {"purchase", "refund"}:
            lottery = await self.session.get(Lottery, UUID(event.payload["lottery"]))
            if lottery is not None and lottery.code == "mini":
                return True
        if event.kind == "draw":
            return await self.draw_page(event)
        if event.kind == "reward":
            return await execute_rewards(
                self.session, UUID(event.payload["award"]), event.occurred_at
            )
        if event.user_id is None:
            raise ValueError("Player event is missing user identity")
        player = await self.player(event.user_id)
        metrics = dict(player.metrics)
        changed: set[str] = set()
        p = event.payload

        def add(metric: str, delta: int, scope: str = "") -> None:
            key = metric_key(metric, scope)
            metrics[key] = metrics.get(key, 0) + delta
            changed.add(key)

        if event.kind in {"purchase", "refund"}:
            lottery = await self.session.get(Lottery, UUID(p["lottery"]))
            assert lottery is not None
            sign = -1 if event.kind == "refund" else 1
            for scope in ("", lottery.code):
                old_paid = metrics.get(metric_key("paid_tickets", scope), 0)
                add("paid_tickets", sign * p["count"], scope)
                add("spent_tickets", sign * p["spent"], scope)
                if scope:
                    new_paid = old_paid + sign * p["count"]
                    add("lotteries_count", int(new_paid > 0) - int(old_paid > 0))
            add("manual_tickets", sign * p.get("manual", 0))
            if (
                sign > 0
                and p.get("operation")
                and not metrics.get("bulk_purchases")
                and self.catalog.watchers.get("bulk_purchases")
            ):
                # A committed purchase is a frozen fact. Later refunds correct
                # incomplete counters, not milestones met at that purchase.
                # Including refunded rows makes awards independent of worker lag.
                paid_count = await self.session.scalar(
                    select(func.count())
                    .select_from(Ticket)
                    .where(
                        Ticket.purchase_operation_id == UUID(p["operation"]),
                        Ticket.user_id == player.user_id,
                        Ticket.purchase_price > 0,
                    )
                )
                if paid_count and paid_count >= 5 and not metrics.get("bulk_purchases"):
                    add("bulk_purchases", 1)
            for draw_id in (p["draw"], p.get("second_draw")):
                if draw_id:
                    delta = await self.participation(
                        player.user_id, UUID(draw_id), sign * p["count"]
                    )
                    if delta:
                        add("draw_participations", delta)
                        add("draw_participations", delta, lottery.code)
            if self.extended:
                changed.update(
                    await self.extended.purchase(event, lottery.code, metrics)
                )
            if sign < 0:
                # Never revoke awards or debit rewards after a refund.
                self.session.add(
                    AchievementCorrection(
                        user_id=player.user_id,
                        event_key=event.event_key,
                        details={"reason": "ticket_refund", **p},
                    )
                )
        elif event.kind == "wallet":
            add("current_balance", p["delta"])
            maximum = max(metrics.get("max_balance", 0), p["maximum"])
            if maximum != metrics.get("max_balance", 0):
                metrics["max_balance"] = maximum
                changed.add("max_balance")
            add("spent_cas", p["spent"])
            add("received_game_cas", p["game"])
        elif event.kind == "activity":
            day = event.occurred_at.astimezone(MOSCOW).date()
            increment, streak = activity_progress(
                player.last_active_day, day, metrics.get("streak", 0)
            )
            add("active_days", increment)
            if increment:
                metrics["streak"] = streak
                metrics["max_streak"] = max(streak, metrics.get("max_streak", 0))
                changed.update(("streak", "max_streak"))
                player.last_active_day = day.isoformat()
            player.last_active_at = max(
                player.last_active_at or event.occurred_at, event.occurred_at
            )
        elif event.kind == "instant":
            ticket = await self.session.get(InstantTicket, UUID(p["ticket"]))
            assert ticket is not None
            result = instant_result(ticket)
            for scope in ("", result["lottery"]):
                old_paid = metrics.get(metric_key("paid_tickets", scope), 0)
                add("paid_tickets", 1, scope)
                add("spent_tickets", ticket.purchase_price, scope)
                if scope and not old_paid:
                    add("lotteries_count", 1)
            self.result_metrics(metrics, changed, result)
            if self.extended:
                changed.update(await self.extended.instant(ticket, result, metrics))
        elif event.kind == "gift_received":
            add("gift_tickets", 1)
            add("gift_tickets", 1, p["lottery"])
        elif event.kind == "reward_paid":
            add("rewarded_achievements", 1)
        elif event.kind in {"baseline", "evaluate"}:
            changed.update(self.catalog.watchers)
        elif event.kind in EVENT_ADAPTERS:
            changed.update(
                await EVENT_ADAPTERS[event.kind](self.session, player, metrics, event)
            )
        else:
            raise ValueError("Unsupported achievement event")
        if any(
            value < 0
            for key, value in metrics.items()
            if key.split(":")[0] not in {"profit_cas"}
        ):
            raise ValueError("Achievement projection underflow")
        player.metrics = metrics
        player.updated_at = datetime.now(UTC)
        if self.award_enabled:
            await self.evaluate(player, changed, event)
        return True

    async def participation(self, user_id: UUID, draw_id: UUID, delta: int) -> int:
        item = await self.session.get(AchievementParticipation, (user_id, draw_id))
        old = item.tickets if item else 0
        new = old + delta
        if new < 0:
            raise ValueError("Participation projection underflow")
        if item:
            item.tickets = new
        else:
            self.session.add(
                AchievementParticipation(user_id=user_id, draw_id=draw_id, tickets=new)
            )
        return int(new > 0) - int(old > 0)

    def result_metrics(
        self, metrics: dict[str, int], changed: set[str], result: dict[str, Any]
    ) -> None:
        prize = result["prize"]
        if prize > 0 and not metrics.get(
            metric_key("winning_tickets", result["lottery"]), 0
        ):
            metrics["winning_lotteries"] = metrics.get("winning_lotteries", 0) + 1
            changed.add("winning_lotteries")
        for scope in ("", result["lottery"]):
            for name, delta in (
                ("winning_tickets", int(prize > 0)),
                ("prizes_count", result["prizes"]),
                ("won_cas", prize),
                ("profit_cas", prize - result["paid"]),
                ("jackpots", int(result["natural_jackpot"])),
            ):
                key = metric_key(name, scope)
                metrics[key] = metrics.get(key, 0) + delta
                if delta:
                    changed.add(key)
            key = metric_key("max_ticket_win", scope)
            if prize > metrics.get(key, 0):
                metrics[key] = prize
                changed.add(key)
        filters = {
            **self.catalog.result_filters.get("", {}),
            **self.catalog.result_filters.get(result["lottery"], {}),
        }
        for key, condition in filters.items():
            if condition.matches_result(result):
                metrics[key] = metrics.get(key, 0) + 1
                changed.add(key)

    async def draw_page(self, event: AchievementEvent) -> bool:
        draw_id = UUID(event.payload["draw"])
        draw = await self.session.get(Draw, draw_id)
        assert draw is not None
        lottery = await self.session.get(Lottery, draw.lottery_id)
        assert lottery is not None
        if lottery.code == "mini":
            return True
        runtime = await self.session.get(AchievementRuntime, 1)
        assert runtime is not None and runtime.started_at is not None
        query = select(Ticket).where(
            Ticket.status == TicketStatus.SETTLED,
            Ticket.purchased_at >= runtime.started_at,
            Ticket.purchase_price > 0,
            or_(
                and_(Ticket.draw_id == draw_id, Ticket.second_draw_id.is_(None)),
                Ticket.second_draw_id == draw_id,
            ),
        )
        if event.cursor:
            query = query.where(Ticket.id > UUID(event.cursor))
        tickets = list(
            (
                await self.session.scalars(
                    query.order_by(Ticket.id).limit(PAGE_SIZE + 1)
                )
            ).all()
        )
        # One player load and one earned-set read per page, never per ticket.
        has_more = len(tickets) > PAGE_SIZE
        tickets = tickets[:PAGE_SIZE]
        for ticket in tickets:
            player = await self.player(ticket.user_id)
            metrics, changed = dict(player.metrics), set[str]()
            result = ticket_result(ticket, draw, lottery)
            self.result_metrics(metrics, changed, result)
            if self.extended:
                changed.update(
                    await self.extended.win(
                        ticket.user_id, result, draw.scheduled_at, metrics, draw=draw
                    )
                )
            player.metrics = metrics
            player.updated_at = datetime.now(UTC)
            if self.award_enabled:
                await self.evaluate(player, changed, event)
        if tickets:
            event.cursor = str(tickets[-1].id)
        return not has_more

    async def value(
        self, player: AchievementPlayer, condition: Condition, now: datetime
    ) -> int:
        if condition.metric == "earned_period":
            if player.user_id not in self.earned_times:
                self.earned_times[player.user_id] = sorted(
                    (
                        await self.session.scalars(
                            select(AchievementAward.earned_at).where(
                                AchievementAward.user_id == player.user_id
                            )
                        )
                    ).all()
                )
            start = now - timedelta(days=condition.period_days or 1)
            values = self.earned_times[player.user_id]
            return bisect_right(values, now) - bisect_left(values, start)
        return player.metrics.get(condition.key, 0)

    async def evaluate(
        self, player: AchievementPlayer, changed: set[str], event: AchievementEvent
    ) -> None:
        candidates = set().union(
            *(self.catalog.watchers.get(k, set()) for k in changed)
        )
        if not candidates:
            return
        if player.user_id not in self.earned:
            rows = list(
                (
                    await self.session.execute(
                        select(AchievementAward.code, AchievementAward.earned_at).where(
                            AchievementAward.user_id == player.user_id
                        )
                    )
                ).all()
            )
            self.earned[player.user_id] = {row[0] for row in rows}
            self.earned_times[player.user_id] = sorted(row[1] for row in rows)
        earned = self.earned[player.user_id]
        now = datetime.now(UTC)
        # At most one award per catalog entry; reward cascades use separate events.
        while candidates:
            next_candidates: set[str] = set()
            for code in sorted(candidates - earned):
                definition = self.catalog.definitions[code]
                rule = self.catalog.rules[code]
                checks = [
                    c.accepts(await self.value(player, c, now)) for c in rule.conditions
                ]
                if not (all(checks) if rule.mode == "all" else any(checks)):
                    continue
                earned.add(code)
                award = AchievementAward(
                    id=uuid4(),
                    user_id=player.user_id,
                    code=code,
                    version=definition.version,
                    rarity=definition.rarity,
                    snapshot=definition_snapshot(definition),
                    earned_at=now,
                    event_key=event.event_key,
                    reward_status=(
                        "awaiting_config"
                        if definition.reward_pending
                        else "pending"
                        if definition.rewards
                        else "completed"
                    ),
                )
                self.session.add(award)
                await self.session.flush()
                insort(self.earned_times[player.user_id], now)
                for position, payload in enumerate(definition.rewards):
                    self.session.add(
                        AchievementReward(
                            id=uuid4(),
                            award_id=award.id,
                            position=position,
                            payload=payload,
                            status="planned" if payload.get("planned") else "pending",
                        )
                    )
                if definition.rewards:
                    await enqueue(
                        self.session,
                        f"reward:{award.id}",
                        "reward",
                        {"award": str(award.id)},
                        player.user_id,
                    )
                await queue_award_notifications(self.session, player, award)
                metrics = dict(player.metrics)
                for key in ("earned", metric_key("earned_category", definition.rarity)):
                    metrics[key] = metrics.get(key, 0) + 1
                    next_candidates.update(self.catalog.watchers.get(key, set()))
                for key in self.catalog.earned_dependencies.get(code, set()):
                    metrics[key] = metrics.get(key, 0) + 1
                    next_candidates.update(self.catalog.watchers.get(key, set()))
                for key, watchers in self.catalog.watchers.items():
                    if key == "earned_period":
                        next_candidates.update(watchers)
                player.metrics = metrics
            candidates = next_candidates - earned


def definition_snapshot(d: AchievementDefinition) -> dict[str, Any]:
    return {
        name: getattr(d, name)
        for name in (
            "code",
            "version",
            "rarity",
            "title",
            "description",
            "flavor",
            "secret",
            "icon",
            "condition",
            "rewards",
            "reward_pending",
        )
    }


async def enqueue(
    session: AsyncSession,
    key: str,
    kind: str,
    payload: dict[str, Any],
    user_id: UUID | None = None,
    *,
    occurred_at: datetime | None = None,
) -> None:
    values: dict[str, Any] = dict(
        event_key=key, kind=kind, payload=payload, user_id=user_id
    )
    if occurred_at:
        values["occurred_at"] = occurred_at
    await session.execute(
        insert(AchievementEvent)
        .values(**values)
        .on_conflict_do_nothing(index_elements=[AchievementEvent.event_key])
    )


async def record_activity(session: AsyncSession, user_id: UUID, now: datetime) -> None:
    runtime = await session.get(AchievementRuntime, 1)
    if runtime is None or not runtime.enabled:
        return
    day = now.astimezone(MOSCOW).date().isoformat()
    await enqueue(
        session, f"activity:{user_id}:{day}", "activity", {}, user_id, occurred_at=now
    )


async def queue_award_notifications(
    session: AsyncSession, player: AchievementPlayer, award: AchievementAward
) -> None:
    # Transport is opt-in and disabled until final copy/catalog approval.
    key = f"achievement:{award.id}"
    session.add(
        UserNotification(
            id=uuid4(),
            event_key=key,
            user_id=player.user_id,
            type=InAppNotificationType.ACHIEVEMENT,
            title="Получено достижение",
            body=award.snapshot["title"],
            payload={"achievement": award.code, "award": str(award.id)},
            created_at=award.earned_at,
        )
    )
    if (
        get_settings().achievements_notifications_enabled
        and player.telegram_enabled
        and award.rarity in {"epic", "legendary"}
    ):
        session.add(
            NotificationOutbox(
                id=uuid4(),
                event_key=key,
                user_id=player.user_id,
                type=NotificationType.ACHIEVEMENT,
                payload={"title": award.snapshot["title"], "award": str(award.id)},
            )
        )


async def execute_rewards(session: AsyncSession, award_id: UUID, now: datetime) -> bool:
    from k_loto.application.economy import require_open

    await require_open(session)
    award = await session.get(AchievementAward, award_id, with_for_update=True)
    assert award is not None
    if award.snapshot.get("reward_pending"):
        raise ValueError("Achievement reward amounts have not been approved")
    parts = list(
        (
            await session.scalars(
                select(AchievementReward)
                .where(AchievementReward.award_id == award_id)
                .where(AchievementReward.parent_id.is_(None))
                # Existing unique (award_id, position) index: never scan the
                # growing list of issued ticket units when resuming a package.
                .where(AchievementReward.position < 16)
                .order_by(AchievementReward.position)
                .with_for_update()
            )
        ).all()
    )
    # One payable part per transaction prevents cross-lottery/fund lock inversions.
    # Expected delivery delays never hold up this player's gameplay events.
    now = datetime.now(UTC)
    for part in parts:
        if part.status != "pending":
            continue
        adapter = REWARD_ADAPTERS.get(part.payload["type"])
        if adapter is None:
            raise ValueError("Reward adapter is unavailable")
        try:
            async with session.begin_nested():
                await adapter(session, award, part)
        except (InsufficientBalance, NoAvailableDraw):
            part.status, part.retry_at = "waiting", now + timedelta(minutes=5)
        else:
            if part.status != "waiting":
                part.status, part.completed_at, part.retry_at = "completed", now, None
        break
    statuses = {p.status for p in parts}
    award.reward_status = (
        "pending"
        if "pending" in statuses
        else "waiting"
        if "waiting" in statuses
        else "planned"
        if "planned" in statuses
        else "completed"
    )
    if award.code != "first_achievement_reward" and any(
        part.payload["type"] == "cas" and part.status == "completed" for part in parts
    ):
        await enqueue(
            session,
            f"reward-paid:{award.id}",
            "reward_paid",
            {"award": str(award.id)},
            award.user_id,
            occurred_at=now,
        )
    return "pending" not in statuses


async def credit_cas(
    session: AsyncSession, award: AchievementAward, part: AchievementReward
) -> None:
    from k_loto.application.weekly import KASPER_FUND_ID

    fund = await session.scalar(
        select(KasperFundAccount)
        .where(KasperFundAccount.id == KASPER_FUND_ID)
        .with_for_update()
    )
    if fund is None:
        raise ValueError("Achievement funding account is missing")
    amount = int(part.payload["amount"])
    if fund.balance < amount:
        raise InsufficientBalance("Achievement funding is temporarily insufficient")
    fund_before = fund.balance
    fund.balance -= amount
    fund.version += 1
    balance = await session.scalar(
        select(Balance).where(Balance.user_id == award.user_id).with_for_update()
    )
    if balance is None:
        raise ValueError("Reward balance is missing")
    before = balance.amount
    if before + amount > 9_000_000_000_000_000_000:
        raise ValueError("Reward balance overflow")
    balance.amount += amount
    balance.version += 1
    session.add(
        _ledger_entry(
            operation_id=part.id,
            idempotency_key=f"achievement:{award.id}:part:{part.position}:fund",
            account_kind=LedgerAccountKind.KASPER_FUND,
            account_id=fund.id,
            transaction_type=TransactionType.ACHIEVEMENT_REWARD,
            before=fund_before,
            after=fund.balance,
            user_id=award.user_id,
            details={
                "achievement": award.code,
                "reward": str(part.id),
                "funding": "kasper_fund",
            },
        )
    )
    session.add(
        _ledger_entry(
            operation_id=part.id,
            idempotency_key=f"achievement:{award.id}:part:{part.position}",
            account_kind=LedgerAccountKind.USER_BALANCE,
            account_id=award.user_id,
            transaction_type=TransactionType.ACHIEVEMENT_REWARD,
            before=before,
            after=balance.amount,
            user_id=award.user_id,
            details={
                "achievement": award.code,
                "version": award.version,
                "reward": str(part.id),
            },
        )
    )


RewardAdapter = Callable[
    [AsyncSession, AchievementAward, AchievementReward], Awaitable[None]
]
REWARD_ADAPTERS: dict[str, RewardAdapter] = {"cas": credit_cas}


async def deliver_ticket(
    session: AsyncSession, award: AchievementAward, part: AchievementReward
) -> None:
    from k_loto.application.weekly import LotteryTicketPurchaseService
    from k_loto.domain.achievement_gifts import gift_draw_capacity
    from k_loto.domain.bingo import POOL_SIZE
    from k_loto.domain.enums import TicketSource
    from k_loto.domain.errors import InvalidTicket
    from k_loto.domain.lottery_rules import get_lottery_rules
    from k_loto.domain.weekly import SystemRandomNumberGenerator

    code = part.payload["lottery"]
    lottery = await session.scalar(
        select(Lottery).where(Lottery.code == code, Lottery.is_active.is_(True))
    )
    if lottery is None:
        raise NoAvailableDraw("Gift lottery is temporarily unavailable")
    now = datetime.now(UTC)
    owned = (
        select(func.count(Ticket.id))
        .where(Ticket.draw_id == Draw.id, Ticket.user_id == award.user_id)
        .correlate(Draw)
        .scalar_subquery()
    )
    draw = await session.scalar(
        select(Draw)
        .where(
            Draw.lottery_id == lottery.id,
            Draw.status == "SCHEDULED",
            Draw.sales_close_at > now,
            owned < gift_draw_capacity(lottery),
            Draw.ticket_count < POOL_SIZE if code == "bingo" else true(),
        )
        .order_by(Draw.scheduled_at)
        .limit(1)
    )
    if draw is None:
        raise NoAvailableDraw("No eligible open draw for the gift ticket")
    rules = get_lottery_rules(
        str(draw.configuration_snapshot.get("ruleset_code", lottery.ruleset_code))
    )
    combination = rules.generate_purchase_combination(SystemRandomNumberGenerator())
    try:
        await LotteryTicketPurchaseService(
            session, lottery_code=code, target_draw_id=draw.id
        ).purchase(
            user_id=award.user_id,
            combinations=[combination],
            idempotency_key=f"gift:{part.id}",
            source=TicketSource.GIFT,
            selection_modes=["random"],
            _reward_part_id=part.id,
            select_bingo_pool=code == "bingo",
        )
    except InvalidTicket as error:
        if "per-player ticket limit" in str(error):
            raise NoAvailableDraw("Gift draw filled during delivery") from error
        raise
    await enqueue(
        session,
        f"gift-received:{part.id}",
        "gift_received",
        {"lottery": lottery.code},
        award.user_id,
    )


REWARD_ADAPTERS["ticket"] = deliver_ticket
REWARD_ADAPTERS["ticket_pack"] = deliver_pack
REWARD_ADAPTERS["cosmetic"] = grant_cosmetic


async def queue_waiting_rewards(factory: async_sessionmaker[AsyncSession]) -> None:
    """Bounded indexed retry queue; planned cases are never selected."""
    async with factory() as session, session.begin():
        if not await worker_lock(session):
            return
        await session.execute(text("SET LOCAL lock_timeout = '250ms'"))
        await session.execute(text("SET LOCAL statement_timeout = '2s'"))
        runtime = await session.get(AchievementRuntime, 1)
        if not runtime or not runtime.enabled or runtime.processing_paused:
            return
        parts = list(
            (
                await session.scalars(
                    select(AchievementReward)
                    .where(
                        AchievementReward.status == "waiting",
                        AchievementReward.retry_at <= datetime.now(UTC),
                    )
                    .order_by(AchievementReward.retry_at, AchievementReward.id)
                    .limit(20)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for part in parts:
            assert part.retry_at is not None
            award = await session.get(AchievementAward, part.award_id)
            assert award is not None
            await enqueue(
                session,
                f"reward-retry:{part.id}:{part.retry_at.isoformat()}",
                "reward",
                {"award": str(award.id)},
                award.user_id,
            )
            part.status, part.retry_at = "pending", None


def register_reward_adapter(kind: str, adapter: RewardAdapter) -> None:
    if kind in REWARD_ADAPTERS:
        raise ValueError("Reward adapter is already registered")
    REWARD_ADAPTERS[kind] = adapter


async def process_one(factory: async_sessionmaker[AsyncSession]) -> bool:
    event_id: int | None = None
    try:
        async with factory() as session, session.begin():
            if not await worker_lock(session):
                return False
            await session.execute(text("SET LOCAL lock_timeout = '250ms'"))
            await session.execute(text("SET LOCAL statement_timeout = '2s'"))
            runtime = await session.get(AchievementRuntime, 1)
            if runtime is None or not runtime.enabled or runtime.processing_paused:
                return False
            # A failed event blocks only later events of the same player; an
            # unfinished draw is a batch job, and yields between pages.
            previous = AchievementEvent.__table__.alias("previous")
            event = await session.scalar(
                select(AchievementEvent)
                .where(
                    AchievementEvent.processed_at.is_(None),
                    AchievementEvent.attempts < 8,
                    AchievementEvent.available_at <= datetime.now(UTC),
                    ~select(previous.c.id)
                    .where(
                        previous.c.processed_at.is_(None),
                        previous.c.user_id == AchievementEvent.user_id,
                        previous.c.id < AchievementEvent.id,
                    )
                    .exists(),
                )
                .order_by(AchievementEvent.available_at, AchievementEvent.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if event is None:
                return False
            event_id = event.id
            projection = AchievementProjection(
                session, await Catalog.cached(session, runtime.catalog_revision)
            )
            done = await projection.apply(event)
            event.processed_at = datetime.now(UTC) if done else None
            if not done:
                event.available_at = datetime.now(UTC) + timedelta(milliseconds=10)
            event.last_error = None
            return True
    except Exception as error:
        if event_id is None:
            raise
        async with factory() as session, session.begin():
            event = await session.scalar(
                select(AchievementEvent)
                .where(AchievementEvent.id == event_id)
                .with_for_update()
            )
            if event is not None and event.processed_at is None:
                event.attempts += 1
                event.last_error = type(error).__name__[:80]
                event.available_at = datetime.now(UTC) + timedelta(
                    seconds=min(300, 2 ** min(event.attempts, 8))
                )
        return True


async def drain(factory: async_sessionmaker[AsyncSession], *, limit: int = 20) -> int:
    await queue_waiting_rewards(factory)
    count = 0
    for _ in range(limit):
        if not await process_one(factory):
            break
        count += 1
    return count
