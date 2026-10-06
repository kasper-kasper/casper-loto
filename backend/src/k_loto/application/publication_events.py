"""Shared nonvisual event stage of the existing Publication draft workflow.

Automatic is eligibility, not permission to deliver. No renderer or transport here.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from importlib.resources import files
from typing import Any, Literal, cast
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import CompoundSelect, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.publications import PublicationConflict, PublicationService
from k_loto.domain.enums import DrawStatus, LedgerAccountKind, TicketStatus
from k_loto.infrastructure.database.models import (
    Draw,
    InstantTicket,
    JackpotAccount,
    JackpotWinEvent,
    LedgerTransaction,
    Lottery,
    Publication,
    PublicationEventState,
    Ticket,
    User,
)


@dataclass(frozen=True)
class EventDefinition:
    code: str
    label: str
    mode: Literal["automatic", "draft"]
    scope: str = "platform"


EVENTS = {
    code: EventDefinition(code, label, cast(Literal["automatic", "draft"], mode))
    for code, label, mode in (
        ("B1.1", "Общее количество игроков", "automatic"),
        ("B1.2", "Купленные билеты", "automatic"),
        ("B1.3", "Завершённые тиражи", "automatic"),
        ("B1.4", "Выигрышные билеты", "automatic"),
        ("B2.1", "Абсолютный рекорд джекпота", "automatic"),
        ("B3.1", "Общий текущий джекпот", "draft"),
        ("B3.2", "Выигрышные билеты сегодня", "draft"),
        ("B3.3", "Активность за неделю", "draft"),
        ("B3.4", "Самая популярная лотерея периода", "draft"),
        ("B3.5", "Несколько джекпотов за день", "automatic"),
        ("B4.1", "Новая функция", "draft"),
        ("B4.2", "Крупное обновление", "draft"),
        ("B4.3", "Изменение интерфейса / редизайн", "draft"),
        ("B4.4", "Новый раздел", "draft"),
        ("B4.5", "Новая платформа", "draft"),
        ("B4.6", "Новые возможности аккаунта", "draft"),
        ("B4.7", "Интеграция / системное расширение", "draft"),
        ("B4.8", "Большой релиз / новая версия", "draft"),
    )
}
LOTTERY_EVENTS: dict[str, EventDefinition] = {}


class MilestoneRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    metric: str
    thresholds: list[int]
    repeat_after: int | None = Field(default=None, ge=1)
    repeat_step: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def valid_grid(self) -> "MilestoneRule":
        if self.thresholds != sorted(set(self.thresholds)) or any(
            n <= 0 for n in self.thresholds
        ):
            raise ValueError("Thresholds must be positive, unique and increasing.")
        if (self.repeat_after is None) != (self.repeat_step is None):
            raise ValueError("Continuation requires both start and step.")
        if (
            self.repeat_after is not None
            and self.thresholds
            and self.repeat_after < self.thresholds[-1]
        ):
            raise ValueError("Continuation must follow the explicit grid.")
        return self

    def reached(self, value: int) -> list[int]:
        thresholds = [n for n in self.thresholds if n <= value]
        if self.repeat_after is not None and self.repeat_step is not None:
            thresholds.extend(
                range(self.repeat_after + self.repeat_step, value + 1, self.repeat_step)
            )
        return thresholds


class DeliveryPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    minimum_interval_seconds: int = Field(ge=1)
    daily_limit: None = None
    combine_blocks: Literal[False] = False

    def earliest(
        self, now: datetime, last_sent_at: datetime | None, *, manual: bool = False
    ) -> datetime:
        require_utc(now)
        if manual or last_sent_at is None:
            return now
        require_utc(last_sent_at)
        return max(now, last_sent_at + timedelta(seconds=self.minimum_interval_seconds))


class EventConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1]
    timezone: Literal["Europe/Moscow"]
    scan_times: list[str]
    delivery: DeliveryPolicy
    milestones: dict[str, MilestoneRule]
    daily_jackpots_minimum: int = Field(ge=1)
    include_instant_tickets: bool

    @model_validator(mode="after")
    def valid_rules(self) -> "EventConfig":
        expected = {
            "B1.1": "registered_players",
            "B1.2": "purchased_tickets",
            "B1.3": "completed_draws",
            "B1.4": "winning_tickets",
        }
        if {k: v.metric for k, v in self.milestones.items()} != expected:
            raise ValueError("Unsupported milestone metric assignment.")
        if not self.scan_times or len(set(self.scan_times)) != len(self.scan_times):
            raise ValueError("Unique scan times required.")
        for slot in self.scan_times:
            time.fromisoformat(slot)
        return self


def event_config() -> EventConfig:
    # Read each invocation: changing a deployed grid does not require engine edits.
    return EventConfig.model_validate_json(
        files("k_loto.application")
        .joinpath("publication_event_config.json")
        .read_text(encoding="utf-8")
    )


def require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("An aware UTC timestamp is required.")


def day_bounds(day: date, timezone: str = "Europe/Moscow") -> tuple[datetime, datetime]:
    zone = ZoneInfo(timezone)
    return (
        datetime.combine(day, time.min, zone).astimezone(UTC),
        datetime.combine(day + timedelta(days=1), time.min, zone).astimezone(UTC),
    )


def due_slot(now: datetime, config: EventConfig) -> str:
    require_utc(now)
    local = now.astimezone(ZoneInfo(config.timezone))
    slots = sorted(time.fromisoformat(s) for s in config.scan_times)
    today = [s for s in slots if s <= local.time().replace(tzinfo=None)]
    day = local.date() if today else local.date() - timedelta(days=1)
    slot = today[-1] if today else slots[-1]
    return f"{day.isoformat()}T{slot.isoformat(timespec='minutes')}"


def event_content(
    code: str,
    payload: dict[str, Any],
    now: datetime,
    *,
    batch: str,
    ready_after: datetime | None = None,
) -> dict[str, Any]:
    require_utc(now)
    definition = EVENTS.get(code) or LOTTERY_EVENTS[code]
    return {
        "schema_version": 1,
        "event": {
            "type": code,
            "block": code[0],
            "category": code.split(".")[0],
            "scope": definition.scope,
            "mode": definition.mode,
            "occurred_at": now.isoformat(),
            "payload": payload,
        },
        "delivery": {
            "state": "awaiting_content_and_visual",
            "batch_key": batch,
            "ready_after": (ready_after or now).isoformat(),
        },
    }


class EventDraftInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_type: str
    fields: dict[str, str] = Field(default_factory=dict)
    period_start: datetime | None = None
    period_end: datetime | None = None

    @model_validator(mode="after")
    def valid_draft(self) -> "EventDraftInput":
        if self.event_type not in EVENTS or EVENTS[self.event_type].mode != "draft":
            raise ValueError("Only supported draft event types may be authored.")
        if len(self.fields) > 12 or any(
            len(k) > 80 or len(v) > 4000 for k, v in self.fields.items()
        ):
            raise ValueError("Draft copy is too large.")
        if self.event_type in ("B3.3", "B3.4"):
            if self.period_start is None or self.period_end is None:
                raise ValueError("Explicit period required; no recurring summaries.")
            require_utc(self.period_start)
            require_utc(self.period_end)
            if self.period_start >= self.period_end:
                raise ValueError("Invalid period.")
            if (
                self.event_type == "B3.3"
                and self.period_end - self.period_start != timedelta(days=7)
            ):
                raise ValueError("Weekly activity requires a seven-day period.")
        return self


class PublicationEventService:
    def __init__(
        self, session: AsyncSession, config: EventConfig | None = None
    ) -> None:
        self.session = session
        self.config = config or event_config()

    async def _lock(self) -> None:
        # All scheduled scans and owner-generated event drafts share this lock.
        await self.session.execute(
            select(
                func.pg_advisory_xact_lock(func.hashtext("publication-event-engine"))
            )
        )

    async def _count(self, model: Any, *conditions: Any) -> int:
        return int(
            await self.session.scalar(
                select(func.count()).select_from(model).where(*conditions)
            )
            or 0
        )

    async def _state(self, key: str) -> PublicationEventState:
        row = await self.session.get(PublicationEventState, key)
        if row is None:
            row = PublicationEventState(key=key, value={})
            self.session.add(row)
            await self.session.flush()
        return row

    async def _store(
        self,
        key: str,
        code: str,
        payload: dict[str, Any],
        now: datetime,
        author: UUID,
        batch: str,
        *,
        refresh: bool = False,
        ready_after: datetime | None = None,
        publication_id: UUID | None = None,
    ) -> Publication:
        row = await self.session.scalar(
            select(Publication).where(Publication.event_key == key).with_for_update()
        )
        if row is not None:
            if (
                refresh
                and row.status == "draft"
                and "template" not in row.content
                and row.content["event"]["payload"] != payload
            ):
                # Refresh draft aggregates, never published history.
                old = dict(row.content)
                row.content = event_content(
                    code, payload, now, batch=batch, ready_after=ready_after
                )
                row.revision += 1
                row.updated_at = now
                PublicationService(self.session)._audit(
                    row, author, "event_refresh", old
                )
            return row
        row = Publication(
            id=publication_id or uuid4(),
            author_id=author,
            lottery_code="casper-loto",
            status="draft",
            revision=1,
            event_type=code,
            event_key=key,
            event_mode=(EVENTS.get(code) or LOTTERY_EVENTS[code]).mode,
            content=event_content(
                code, payload, now, batch=batch, ready_after=ready_after
            ),
            created_at=now,
            updated_at=now,
        )
        self.session.add(row)
        PublicationService(self.session)._audit(row, author, "event_create", None)
        await self.session.flush()
        return row

    async def metrics(self) -> dict[str, int]:
        purchased = await self._count(Ticket)
        winners = await self._count(
            Ticket, Ticket.status == TicketStatus.SETTLED, Ticket.prize_amount > 0
        )
        if self.config.include_instant_tickets:
            purchased += await self._count(InstantTicket)
            winners += await self._count(InstantTicket, InstantTicket.prize_amount > 0)
        return {
            "registered_players": await self._count(User),
            "purchased_tickets": purchased,
            "completed_draws": await self._count(
                Draw, Draw.status == DrawStatus.COMPLETED
            ),
            "winning_tickets": winners,
        }

    async def scan(
        self, *, now: datetime, force: bool = False, author: UUID | None = None
    ) -> dict[str, Any]:
        require_utc(now)
        async with self.session.begin():
            await self._lock()
            checkpoint = await self._state("B.scan")
            slot = due_slot(now, self.config)
            if not force and checkpoint.value.get("slot", "") >= slot:
                return {"skipped": True, "slot": slot}
            if author is None:
                author = await self.session.scalar(
                    select(User.id)
                    .where(User.is_admin.is_(True))
                    .order_by(User.created_at, User.id)
                    .limit(1)
                )
            if author is None:
                raise ValueError("An existing admin author is required.")
            counters = await self.metrics()
            batch = f"B:scan:{slot}"
            for code, rule in self.config.milestones.items():
                for threshold in rule.reached(counters[rule.metric]):
                    await self._store(
                        f"{code}:milestone:{threshold}",
                        code,
                        {
                            "metric": rule.metric,
                            "threshold": threshold,
                            "observed_value": counters[rule.metric],
                            "metric_version": 1,
                        },
                        now,
                        author,
                        batch,
                    )
            await self._record(now, author, batch)
            await self._daily_jackpots(now, author)
            checkpoint.value = {
                "slot": max(slot, checkpoint.value.get("slot", "")),
                "last_scan_at": now.isoformat(),
                "counters": counters,
                "config_version": self.config.version,
            }
            await self.session.flush()
            return {
                "skipped": False,
                "slot": slot,
                "counters": counters,
                "delivery_enabled": False,
            }

    async def _record(self, now: datetime, author: UUID, batch: str) -> None:
        record = await self._state("B2.1.record")
        historical = int(
            await self.session.scalar(
                select(
                    func.max(func.greatest(Draw.jackpot_opening, Draw.jackpot_closing))
                ).where(Draw.status == DrawStatus.COMPLETED)
            )
            or 0
        )
        won = int(
            await self.session.scalar(select(func.max(JackpotWinEvent.jackpot_amount)))
            or 0
        )
        baseline = max(historical, won, int(record.value.get("value", 0)))
        if not record.value:
            # Bootstrap from immutable financial history, including intra-draw peaks.
            ledger_peak = int(
                await self.session.scalar(
                    select(
                        func.max(
                            func.greatest(
                                LedgerTransaction.balance_before,
                                LedgerTransaction.balance_after,
                            )
                        )
                    ).where(LedgerTransaction.account_kind == LedgerAccountKind.JACKPOT)
                )
                or 0
            )
            baseline = max(baseline, ledger_peak)
        if not record.value or baseline > record.value["value"]:
            record.value = {"value": baseline, "source": "historical_baseline"}
        current = (
            await self.session.execute(
                select(
                    JackpotAccount.balance,
                    JackpotAccount.id.label("jackpot_account_id"),
                    Lottery.code,
                    Lottery.id,
                )
                .join(Lottery, Lottery.id == JackpotAccount.lottery_id)
                .order_by(JackpotAccount.balance.desc(), Lottery.code)
                .limit(1)
            )
        ).first()
        if current is None or current.balance <= record.value["value"]:
            return
        payload = {
            "new_record": current.balance,
            "previous_record": record.value["value"],
            "lottery_code": current.code,
            "lottery_id": str(current.id),
            "jackpot_account_id": str(current.jackpot_account_id),
            "observed_at": now.isoformat(),
            "unit": "CAS",
        }
        row = await self._store(
            f"B2.1:record:{current.balance}", "B2.1", payload, now, author, batch
        )
        record.value = {"value": current.balance, "event_id": str(row.id), **payload}

    async def _daily_jackpots(self, now: datetime, author: UUID) -> None:
        # Jackpot wins are rare. Reading the immutable projection catches arbitrarily
        # late recovered draws without a lossy occurrence-time watermark.
        query = (
            select(JackpotWinEvent, Lottery.code)
            .join(Lottery, Lottery.id == JackpotWinEvent.lottery_id)
            .where(JackpotWinEvent.occurred_at <= now)
            .order_by(JackpotWinEvent.occurred_at, JackpotWinEvent.id)
        )
        grouped: dict[date, list[dict[str, Any]]] = {}
        for win, code in (await self.session.execute(query)).all():
            day = win.occurred_at.astimezone(ZoneInfo(self.config.timezone)).date()
            grouped.setdefault(day, []).append(
                {
                    "event_id": str(win.id),
                    "draw_id": str(win.draw_id),
                    "lottery_code": code,
                    "amount": win.jackpot_amount,
                    "occurred_at": win.occurred_at.isoformat(),
                }
            )
        for day, wins in grouped.items():
            if len(wins) >= self.config.daily_jackpots_minimum:
                await self._store(
                    f"B3.5:day:{day.isoformat()}",
                    "B3.5",
                    {
                        "day": day.isoformat(),
                        "timezone": self.config.timezone,
                        "count": len(wins),
                        "jackpots": wins,
                    },
                    now,
                    author,
                    f"B:day:{day.isoformat()}",
                    refresh=True,
                    ready_after=day_bounds(day)[1],
                )

    async def create_draft(
        self,
        request: EventDraftInput,
        *,
        publication_id: UUID,
        author: UUID,
        now: datetime,
    ) -> Publication:
        require_utc(now)
        async with self.session.begin():
            await self._lock()
            key = f"{request.event_type}:draft:{publication_id}"
            existing = await self.session.get(Publication, publication_id)
            source = request.model_dump(mode="json")
            if existing is not None:
                if (
                    existing.author_id != author
                    or existing.event_type != request.event_type
                    or existing.content["event"]["payload"].get("request") != source
                ):
                    raise PublicationConflict("Draft identifier already used.")
                return existing
            if request.period_end is not None and request.period_end > now:
                raise ValueError("Period cannot end in the future.")
            payload: dict[str, Any] = {"request": source}
            if request.event_type == "B3.1":
                payload["total_jackpot"] = int(
                    await self.session.scalar(select(func.sum(JackpotAccount.balance)))
                    or 0
                )
                payload["unit"] = "CAS"
            elif request.event_type == "B3.2":
                day = now.astimezone(ZoneInfo(self.config.timezone)).date()
                start, end = day_bounds(day)
                payload.update(
                    {
                        "day": str(day),
                        "metric": "winning_tickets",
                        "count": await self._winning_period(start, min(end, now)),
                        "timezone": self.config.timezone,
                    }
                )
            elif request.event_type in ("B3.3", "B3.4"):
                assert (
                    request.period_start is not None and request.period_end is not None
                )
                payload.update(
                    await self._activity(request.period_start, request.period_end)
                )
            return await self._store(
                key,
                request.event_type,
                payload,
                now,
                author,
                f"B:draft:{publication_id}",
                publication_id=publication_id,
            )

    async def _winning_period(self, start: datetime, end: datetime) -> int:
        count = await self._count(
            Ticket,
            Ticket.status == TicketStatus.SETTLED,
            Ticket.prize_amount > 0,
            Ticket.settled_at >= start,
            Ticket.settled_at < end,
        )
        if self.config.include_instant_tickets:
            count += await self._count(
                InstantTicket,
                InstantTicket.prize_amount > 0,
                InstantTicket.settled_at >= start,
                InstantTicket.settled_at < end,
            )
        return count

    async def _activity(self, start: datetime, end: datetime) -> dict[str, Any]:
        rows = (
            await self.session.execute(
                select(Lottery.code, func.count(Ticket.id).label("tickets"))
                .join(Ticket, Ticket.lottery_id == Lottery.id)
                .where(Ticket.purchased_at >= start, Ticket.purchased_at < end)
                .group_by(Lottery.code)
            )
        ).all()
        counts = {code: count for code, count in rows}
        draw_participants = select(Ticket.user_id).where(
            Ticket.purchased_at >= start, Ticket.purchased_at < end
        )
        participants: Select[tuple[UUID]] | CompoundSelect[tuple[UUID]] = (
            draw_participants
        )
        if self.config.include_instant_tickets:
            counts["kasper-live"] = await self._count(
                InstantTicket,
                InstantTicket.purchased_at >= start,
                InstantTicket.purchased_at < end,
            )
            participants = draw_participants.union(
                select(InstantTicket.user_id).where(
                    InstantTicket.purchased_at >= start,
                    InstantTicket.purchased_at < end,
                )
            )
        ranking = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        peak = ranking[0][1] if ranking else 0
        leaders = [code for code, count in ranking if count == peak and peak > 0]
        return {
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "purchased_tickets": sum(counts.values()),
            "active_players": int(
                await self.session.scalar(
                    select(func.count(func.distinct(participants.subquery().c.user_id)))
                )
                or 0
            ),
            "winning_tickets": await self._winning_period(start, end),
            "completed_draws": await self._count(
                Draw,
                Draw.status == DrawStatus.COMPLETED,
                Draw.executed_at >= start,
                Draw.executed_at < end,
            ),
            "tickets_by_lottery": counts,
            "popularity_metric": "purchased_tickets",
            "most_popular_lotteries": leaders,
        }
