"""Small event-driven projections for calendar and adjacent-draw conditions."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.domain.schedules import MOSCOW
from k_loto.infrastructure.database.achievement_models import (
    AchievementDay,
    AchievementEvent,
    AchievementWinningDraw,
)
from k_loto.infrastructure.database.models import Draw, InstantTicket

EXTENDED_METRICS = frozenset(
    {
        "daily_play_types",
        "daily_winning_lotteries",
        "consecutive_winning_draws",
        "max_draw_winning_tickets",
        "daily_fast_winning_games",
    }
)
RARE_METRICS = frozenset({"max_draw_winning_tickets", "daily_fast_winning_games"})
SPECIAL_GAMES = frozenset({"september", "pll", "grob"})


class ExtendedProgress:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.days: dict[tuple[UUID, date], AchievementDay] = {}
        self.neighbours: dict[UUID, list[list[UUID]]] = {}
        self.winning_draws: set[tuple[UUID, UUID]] = set()
        self.draw_records: dict[tuple[UUID, UUID], AchievementWinningDraw] = {}

    async def day(self, user_id: UUID, day: date) -> AchievementDay:
        key = (user_id, day)
        if key not in self.days:
            await self.session.execute(
                insert(AchievementDay)
                .values(user_id=user_id, day=day)
                .on_conflict_do_nothing()
            )
            row = await self.session.get(AchievementDay, key)
            assert row is not None
            self.days[key] = row
        return self.days[key]

    async def play(
        self,
        user_id: UUID,
        code: str,
        when: datetime | date,
        delta: int,
        metrics: dict[str, int],
        *,
        instant: bool = False,
    ) -> set[str]:
        day = when.astimezone(MOSCOW).date() if isinstance(when, datetime) else when
        row = await self.day(user_id, day)
        group = "instant" if instant else "special" if code in SPECIAL_GAMES else "draw"
        counts = dict(row.play_counts)
        counts[group] = counts.get(group, 0) + delta
        if counts[group] < 0:
            raise ValueError("Daily paid participation underflow")
        row.play_counts = counts
        row.play_types = sum(value > 0 for value in counts.values())
        if delta < 0:
            await self.session.flush()
            best = await self.session.scalar(
                select(AchievementDay.play_types)
                .where(AchievementDay.user_id == user_id)
                .order_by(AchievementDay.play_types.desc())
                .limit(1)
            )
            metrics["daily_play_types"] = best or 0
        else:
            metrics["daily_play_types"] = max(
                metrics.get("daily_play_types", 0), row.play_types
            )
        return {"daily_play_types"}

    async def purchase(
        self, event: AchievementEvent, code: str, metrics: dict[str, int]
    ) -> set[str]:
        assert event.user_id is not None
        p = event.payload
        day = (
            date.fromisoformat(p["day"])
            if p.get("day")
            else event.occurred_at.astimezone(MOSCOW).date()
        )
        if event.kind == "refund" and not p.get("day"):
            # Compatibility for pre-upgrade events. New events persist purchase day.
            original = await self.session.scalar(
                select(AchievementEvent.occurred_at)
                .where(
                    AchievementEvent.user_id == event.user_id,
                    AchievementEvent.kind == "purchase",
                    AchievementEvent.payload["draw"].astext == p["draw"],
                    AchievementEvent.payload["operation"].astext == p.get("operation"),
                )
                .order_by(AchievementEvent.id)
                .limit(1)
            )
            if original:
                day = original.astimezone(MOSCOW).date()
        return await self.play(
            event.user_id,
            code,
            day,
            (-1 if event.kind == "refund" else 1) * p["count"],
            metrics,
        )

    async def win(
        self,
        user_id: UUID,
        result: dict[str, Any],
        when: datetime,
        metrics: dict[str, int],
        *,
        draw: Draw | None = None,
    ) -> set[str]:
        if result["prize"] <= 0:
            return set()
        code = result["lottery"]
        row = await self.day(user_id, when.astimezone(MOSCOW).date())
        games = set(row.winning_lotteries)
        games.add(code)
        row.winning_lotteries = sorted(games)
        metrics["daily_winning_lotteries"] = max(
            metrics.get("daily_winning_lotteries", 0), len(games)
        )
        metrics["daily_fast_winning_games"] = max(
            metrics.get("daily_fast_winning_games", 0),
            len(games & {"flash", "shadow", "pulse"}),
        )
        changed = {"daily_winning_lotteries", "daily_fast_winning_games"}
        if draw is not None:
            key = (user_id, draw.id)
            if key not in self.draw_records:
                record = await self.session.scalar(
                    insert(AchievementWinningDraw)
                    .values(user_id=user_id, draw_id=draw.id, tickets=1)
                    .on_conflict_do_update(
                        index_elements=[
                            AchievementWinningDraw.user_id,
                            AchievementWinningDraw.draw_id,
                        ],
                        set_={"tickets": AchievementWinningDraw.tickets + 1},
                    )
                    .returning(AchievementWinningDraw)
                    .execution_options(populate_existing=True)
                )
                assert record is not None
                self.draw_records[key] = record
            else:
                self.draw_records[key].tickets += 1
            metrics["max_draw_winning_tickets"] = max(
                metrics.get("max_draw_winning_tickets", 0),
                self.draw_records[key].tickets,
            )
            changed.add("max_draw_winning_tickets")
        if (
            draw is not None
            and metrics.get("consecutive_winning_draws", 0) < 5
            and (user_id, draw.id) not in self.winning_draws
        ):
            self.winning_draws.add((user_id, draw.id))
            metrics["consecutive_winning_draws"] = max(
                1, metrics.get("consecutive_winning_draws", 0)
            )
            if draw.id not in self.neighbours:
                adjacent = []
                for previous in (True, False):
                    query = select(Draw.id).where(
                        Draw.lottery_id == draw.lottery_id,
                        Draw.status == "COMPLETED",
                        Draw.scheduled_at < draw.scheduled_at
                        if previous
                        else Draw.scheduled_at > draw.scheduled_at,
                    )
                    adjacent.append(
                        list(
                            (
                                await self.session.scalars(
                                    query.order_by(
                                        Draw.scheduled_at.desc()
                                        if previous
                                        else Draw.scheduled_at
                                    ).limit(4)
                                )
                            ).all()
                        )
                    )
                self.neighbours[draw.id] = adjacent
            neighbours = self.neighbours[draw.id]
            ids = [value for side in neighbours for value in side]
            won = (
                set(
                    (
                        await self.session.scalars(
                            select(AchievementWinningDraw.draw_id).where(
                                AchievementWinningDraw.user_id == user_id,
                                AchievementWinningDraw.draw_id.in_(ids),
                            )
                        )
                    ).all()
                )
                if ids
                else set()
            )
            length = 1
            for side in neighbours:
                for neighbour_id in side:
                    if neighbour_id not in won:
                        break
                    length += 1
            metrics["consecutive_winning_draws"] = max(
                metrics["consecutive_winning_draws"], min(5, length)
            )
            changed.add("consecutive_winning_draws")
        return changed

    async def instant(
        self, ticket: InstantTicket, result: dict[str, Any], metrics: dict[str, int]
    ) -> set[str]:
        changed = await self.play(
            ticket.user_id,
            result["lottery"],
            ticket.purchased_at,
            1,
            metrics,
            instant=True,
        )
        changed.update(
            await self.win(ticket.user_id, result, ticket.purchased_at, metrics)
        )
        return changed
