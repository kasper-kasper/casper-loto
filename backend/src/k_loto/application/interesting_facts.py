"""Daily, precomputed content ideas for the owner panel."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from itertools import combinations
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import case, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from k_loto.domain.enums import DrawStatus, InterestingFactStatus, TicketStatus
from k_loto.domain.lotteries import MOSCOW
from k_loto.infrastructure.database.models import (
    Draw,
    InterestingFact,
    InterestingFactBatch,
    JackpotAccount,
    Lottery,
    Ticket,
)


@dataclass(frozen=True, slots=True)
class FactLottery:
    id: UUID
    code: str
    name: str
    ruleset_code: str
    max_number: int
    current_jackpot: int
    base_jackpot: int
    historical_jackpot: int
    jackpot_drought: int


@dataclass(frozen=True, slots=True)
class FactDraw:
    lottery_id: UUID
    scheduled_at: datetime
    winning_numbers: tuple[int, ...]
    ticket_count: int
    total_sales: int
    jackpot_opening: int
    jackpot_closing: int


@dataclass(frozen=True, slots=True)
class FactTicketStats:
    lottery_id: UUID
    daily_tickets: int
    daily_winners: int
    daily_largest_win: int
    weekly_tickets: int
    weekly_winners: int
    weekly_largest_win: int
    monthly_tickets: int
    monthly_winners: int


@dataclass(frozen=True, slots=True)
class FactCandidate:
    lottery_id: UUID
    fact_type: str
    title: str
    description: str
    numeric_values: dict[str, Any]
    score: int


@dataclass(frozen=True, slots=True)
class StoredFact:
    id: UUID
    generation_date: date
    generated_at: datetime
    lottery_id: UUID
    lottery_code: str
    lottery_name: str
    fact_type: str
    title: str
    description: str
    numeric_values: dict[str, Any]
    score: int
    status: InterestingFactStatus


def _cas(value: int) -> str:
    return f"{value:,}".replace(",", " ") + " CAS"


def _score(value: float) -> int:
    return max(0, min(100, round(value)))


def build_fact_candidates(
    lotteries: list[FactLottery],
    draws: list[FactDraw],
    ticket_stats: list[FactTicketStats],
    *,
    now: datetime,
) -> list[FactCandidate]:
    """Produce compact structured candidates from one already-loaded snapshot."""
    stats_by_lottery = {row.lottery_id: row for row in ticket_stats}
    draws_by_lottery: dict[UUID, list[FactDraw]] = {}
    for draw in draws:
        draws_by_lottery.setdefault(draw.lottery_id, []).append(draw)
    for rows in draws_by_lottery.values():
        rows.sort(key=lambda item: item.scheduled_at, reverse=True)

    candidates: list[FactCandidate] = []
    seven_days_ago = now - timedelta(days=7)
    one_day_ago = now - timedelta(days=1)
    for lottery in lotteries:
        rows = draws_by_lottery.get(lottery.id, [])
        recent = rows[:30]
        stats = stats_by_lottery.get(lottery.id)

        if lottery.jackpot_drought >= 5:
            candidates.append(
                FactCandidate(
                    lottery.id,
                    "jackpot_drought",
                    f"{lottery.name}: {lottery.jackpot_drought} тиражей без джекпота",
                    "Джекпот продолжает копиться — серия уже заметно растянулась.",
                    {
                        "draws_without_jackpot": lottery.jackpot_drought,
                        "jackpot": lottery.current_jackpot,
                    },
                    _score(48 + lottery.jackpot_drought * 1.8),
                )
            )

        prior_record = max(lottery.historical_jackpot, lottery.base_jackpot)
        if (
            lottery.current_jackpot > lottery.base_jackpot
            and lottery.current_jackpot >= prior_record
        ):
            candidates.append(
                FactCandidate(
                    lottery.id,
                    "record_current_jackpot",
                    f"Рекордный джекпот {lottery.name}",
                    f"Текущий джекпот достиг {_cas(lottery.current_jackpot)} — "
                    "это максимум в сохранённой истории.",
                    {
                        "current_jackpot": lottery.current_jackpot,
                        "base_jackpot": lottery.base_jackpot,
                    },
                    _score(
                        82
                        + 18
                        * (lottery.current_jackpot / max(1, lottery.base_jackpot) - 1)
                    ),
                )
            )

        week_rows = [row for row in rows if row.scheduled_at >= seven_days_ago]
        if week_rows:
            oldest = week_rows[-1].jackpot_opening
            growth = lottery.current_jackpot - oldest
            growth_percent = growth / max(1, oldest) * 100
            if growth > 0 and growth_percent >= 5:
                candidates.append(
                    FactCandidate(
                        lottery.id,
                        "jackpot_growth",
                        f"Джекпот {lottery.name} вырос на {growth_percent:.0f}%",
                        f"За семь дней сумма прибавила {_cas(growth)}.",
                        {
                            "period_days": 7,
                            "growth": growth,
                            "growth_percent": round(growth_percent, 1),
                            "current_jackpot": lottery.current_jackpot,
                        },
                        _score(55 + growth_percent),
                    )
                )

        if len(recent) >= 5 and lottery.code != "bingo":
            frequency = Counter(
                number
                for row in recent
                for number in row.winning_numbers
                if 0 <= number <= lottery.max_number
            )
            frequent = [number for number, _ in frequency.most_common(3)]
            frequent_counts = [frequency[number] for number in frequent]
            candidates.append(
                FactCandidate(
                    lottery.id,
                    "frequent_numbers",
                    f"Частые числа {lottery.name}: {' · '.join(map(str, frequent))}",
                    f"Они появлялись чаще остальных в последних {len(recent)} тиражах.",
                    {
                        "draw_count": len(recent),
                        "numbers": frequent,
                        "appearances": frequent_counts,
                    },
                    _score(48 + max(frequent_counts, default=0) * 4),
                )
            )

            possible = range(
                0 if "code" in lottery.ruleset_code else 1,
                lottery.max_number + 1,
            )
            gaps: dict[int, int] = {}
            for number in possible:
                gaps[number] = next(
                    (
                        index
                        for index, row in enumerate(recent)
                        if number in row.winning_numbers
                    ),
                    len(recent),
                )
            cold = sorted(gaps, key=lambda number: (-gaps[number], number))[:3]
            if cold and gaps[cold[0]] >= 4:
                candidates.append(
                    FactCandidate(
                        lottery.id,
                        "overdue_numbers",
                        f"Давно не выпадали в {lottery.name}: "
                        f"{' · '.join(map(str, cold))}",
                        "Эти числа дольше других не появлялись в недавних результатах.",
                        {
                            "draw_count": len(recent),
                            "numbers": cold,
                            "draws_since_last": [gaps[number] for number in cold],
                        },
                        _score(50 + gaps[cold[0]] * 2),
                    )
                )

            pairs = Counter(
                pair
                for row in recent
                for pair in combinations(
                    sorted(
                        number
                        for number in set(row.winning_numbers)
                        if 0 <= number <= lottery.max_number
                    ),
                    2,
                )
            )
            if pairs:
                pair, pair_count = pairs.most_common(1)[0]
                if pair_count >= 3:
                    candidates.append(
                        FactCandidate(
                            lottery.id,
                            "frequent_pair",
                            f"Пара тиражей {lottery.name}: {pair[0]} и {pair[1]}",
                            f"Эти два числа выпадали вместе {pair_count} раз "
                            f"за последние {len(recent)} тиражей.",
                            {
                                "draw_count": len(recent),
                                "numbers": list(pair),
                                "joint_appearances": pair_count,
                            },
                            _score(45 + pair_count * 6),
                        )
                    )

        if stats and stats.daily_tickets >= 3 and stats.monthly_tickets >= 10:
            daily_rate = stats.daily_winners / stats.daily_tickets * 100
            monthly_rate = stats.monthly_winners / stats.monthly_tickets * 100
            delta = daily_rate - monthly_rate
            if abs(delta) >= 15:
                direction = "выше" if delta > 0 else "ниже"
                candidates.append(
                    FactCandidate(
                        lottery.id,
                        "unusual_win_rate",
                        f"Необычный процент выигрышей в {lottery.name}",
                        f"За сутки выиграли {daily_rate:.0f}% билетов — "
                        f"на {abs(delta):.0f} п.п. {direction} среднего за 30 дней.",
                        {
                            "daily_tickets": stats.daily_tickets,
                            "daily_winners": stats.daily_winners,
                            "daily_percent": round(daily_rate, 1),
                            "monthly_percent": round(monthly_rate, 1),
                            "delta_points": round(delta, 1),
                        },
                        _score(58 + abs(delta)),
                    )
                )

        daily_rows = [row for row in rows if row.scheduled_at >= one_day_ago]
        if daily_rows:
            busiest = max(daily_rows, key=lambda row: row.ticket_count)
            if busiest.ticket_count >= 5:
                candidates.append(
                    FactCandidate(
                        lottery.id,
                        "busiest_draw",
                        f"Самый заметный тираж суток — {lottery.name}",
                        f"В одном тираже участвовало {busiest.ticket_count} билетов "
                        f"на сумму {_cas(busiest.total_sales)}.",
                        {
                            "ticket_count": busiest.ticket_count,
                            "sales": busiest.total_sales,
                        },
                        _score(45 + busiest.ticket_count * 2),
                    )
                )

    populated = [(lottery, stats_by_lottery.get(lottery.id)) for lottery in lotteries]
    daily_leaders = [
        (lottery, stats)
        for lottery, stats in populated
        if stats and stats.daily_winners > 0
    ]
    if daily_leaders:
        lottery, stats = max(daily_leaders, key=lambda item: item[1].daily_winners)
        assert stats is not None
        candidates.append(
            FactCandidate(
                lottery.id,
                "daily_winner_leader",
                f"Больше всего выигрышных билетов за сутки — {lottery.name}",
                f"Выигрыш получили {stats.daily_winners} билетов "
                f"из {stats.daily_tickets}.",
                {
                    "winning_tickets": stats.daily_winners,
                    "settled_tickets": stats.daily_tickets,
                },
                _score(65 + stats.daily_winners * 3),
            )
        )

    daily_wins = [
        (lottery, stats)
        for lottery, stats in populated
        if stats and stats.daily_largest_win > 0
    ]
    if daily_wins:
        lottery, stats = max(daily_wins, key=lambda item: item[1].daily_largest_win)
        assert stats is not None
        candidates.append(
            FactCandidate(
                lottery.id,
                "largest_daily_win",
                f"Крупнейший выигрыш суток — {_cas(stats.daily_largest_win)}",
                f"Он случился в лотерее {lottery.name}.",
                {"prize": stats.daily_largest_win, "period_days": 1},
                _score(76 + stats.daily_largest_win / 1_000_000),
            )
        )

    weekly_wins = [
        (lottery, stats)
        for lottery, stats in populated
        if stats and stats.weekly_largest_win > 0
    ]
    if weekly_wins:
        lottery, stats = max(weekly_wins, key=lambda item: item[1].weekly_largest_win)
        assert stats is not None
        candidates.append(
            FactCandidate(
                lottery.id,
                "largest_weekly_win",
                f"Крупнейший выигрыш недели — {_cas(stats.weekly_largest_win)}",
                f"Главный выигрыш последних семи дней пришёлся на {lottery.name}.",
                {"prize": stats.weekly_largest_win, "period_days": 7},
                _score(82 + stats.weekly_largest_win / 2_000_000),
            )
        )

    return sorted(candidates, key=lambda item: (-item.score, item.title))


class InterestingFactService:
    """Generate once per Moscow day and serve only persisted results."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def run_if_due(self, *, now: datetime | None = None) -> bool:
        generated_at = now or datetime.now(UTC)
        if generated_at.tzinfo is None:
            raise ValueError(
                "Interesting-fact generation time must include a timezone."
            )
        generation_date = generated_at.astimezone(MOSCOW).date()
        async with self._session_factory() as session, session.begin():
            batch_id = await session.scalar(
                insert(InterestingFactBatch)
                .values(
                    id=uuid4(),
                    generation_date=generation_date,
                    candidate_count=0,
                    generated_at=generated_at,
                )
                .on_conflict_do_nothing(
                    index_elements=[InterestingFactBatch.generation_date]
                )
                .returning(InterestingFactBatch.id)
            )
            if batch_id is None:
                return False
            lotteries, draws, stats = await self._snapshot(session, generated_at)
            candidates = build_fact_candidates(
                lotteries, draws, stats, now=generated_at
            )
            session.add_all(
                [
                    InterestingFact(
                        batch_id=batch_id,
                        generation_date=generation_date,
                        generated_at=generated_at,
                        lottery_id=item.lottery_id,
                        fact_type=item.fact_type,
                        title=item.title,
                        description=item.description,
                        numeric_values=item.numeric_values,
                        score=item.score,
                    )
                    for item in candidates
                ]
            )
            await session.execute(
                update(InterestingFactBatch)
                .where(InterestingFactBatch.id == batch_id)
                .values(candidate_count=len(candidates))
            )
        return True

    async def _snapshot(
        self, session: AsyncSession, now: datetime
    ) -> tuple[list[FactLottery], list[FactDraw], list[FactTicketStats]]:
        # Seven days is the largest candidate window. Number facts use only the
        # latest 30 rows from this snapshot, so older draws never leave Postgres.
        history_start = now - timedelta(days=7)
        day_start, week_start, month_start = (
            now - timedelta(days=1),
            now - timedelta(days=7),
            now - timedelta(days=30),
        )
        historical = (
            select(
                Draw.lottery_id,
                func.max(
                    func.greatest(
                        func.coalesce(Draw.jackpot_opening, 0),
                        func.coalesce(Draw.jackpot_closing, 0),
                    )
                ).label("maximum"),
            )
            .where(Draw.status == DrawStatus.COMPLETED)
            .group_by(Draw.lottery_id)
            .subquery()
        )
        from k_loto.application.jackpot_cycles import last_cycle_ends

        last_wins = last_cycle_ends()
        droughts = (
            select(Draw.lottery_id, func.count(Draw.id).label("drought"))
            .outerjoin(last_wins, last_wins.c.lottery_id == Draw.lottery_id)
            .where(
                Draw.status == DrawStatus.COMPLETED,
                Draw.scheduled_at
                > func.coalesce(
                    last_wins.c.last_reset, datetime(1970, 1, 1, tzinfo=UTC)
                ),
            )
            .group_by(Draw.lottery_id)
            .subquery()
        )
        lottery_rows = (
            await session.execute(
                select(
                    Lottery,
                    JackpotAccount.balance,
                    JackpotAccount.base_amount,
                    func.coalesce(historical.c.maximum, 0),
                    func.coalesce(droughts.c.drought, 0),
                )
                .join(JackpotAccount, JackpotAccount.lottery_id == Lottery.id)
                .outerjoin(historical, historical.c.lottery_id == Lottery.id)
                .outerjoin(droughts, droughts.c.lottery_id == Lottery.id)
                .where(Lottery.is_active.is_(True))
            )
        ).all()
        lotteries = [
            FactLottery(
                row.id,
                row.code,
                row.name,
                row.ruleset_code,
                row.max_number,
                balance,
                base,
                maximum,
                drought,
            )
            for row, balance, base, maximum, drought in lottery_rows
        ]
        draw_rows = (
            await session.execute(
                select(
                    Draw.lottery_id,
                    Draw.scheduled_at,
                    Draw.winning_numbers,
                    Draw.ticket_count,
                    Draw.total_sales,
                    Draw.jackpot_opening,
                    Draw.jackpot_closing,
                )
                .where(
                    Draw.status == DrawStatus.COMPLETED,
                    Draw.scheduled_at >= history_start,
                )
                .order_by(Draw.scheduled_at.desc())
            )
        ).all()
        draws = [
            FactDraw(
                lottery_id,
                scheduled_at,
                tuple(numbers or ()),
                tickets,
                sales,
                opening or 0,
                closing or 0,
            )
            for (
                lottery_id,
                scheduled_at,
                numbers,
                tickets,
                sales,
                opening,
                closing,
            ) in draw_rows
            if numbers
        ]
        winner = case((Ticket.prize_amount > 0, 1), else_=0)
        stat_rows = (
            await session.execute(
                select(
                    Ticket.lottery_id,
                    func.count(Ticket.id).filter(Ticket.settled_at >= day_start),
                    func.sum(winner).filter(Ticket.settled_at >= day_start),
                    func.max(Ticket.prize_amount).filter(
                        Ticket.settled_at >= day_start
                    ),
                    func.count(Ticket.id).filter(Ticket.settled_at >= week_start),
                    func.sum(winner).filter(Ticket.settled_at >= week_start),
                    func.max(Ticket.prize_amount).filter(
                        Ticket.settled_at >= week_start
                    ),
                    func.count(Ticket.id),
                    func.sum(winner),
                )
                .where(
                    Ticket.status == TicketStatus.SETTLED,
                    Ticket.settled_at >= month_start,
                )
                .group_by(Ticket.lottery_id)
            )
        ).all()
        stats = [
            FactTicketStats(
                lottery_id,
                daily or 0,
                daily_winners or 0,
                daily_max or 0,
                weekly or 0,
                weekly_winners or 0,
                weekly_max or 0,
                monthly or 0,
                monthly_winners or 0,
            )
            for (
                lottery_id,
                daily,
                daily_winners,
                daily_max,
                weekly,
                weekly_winners,
                weekly_max,
                monthly,
                monthly_winners,
            ) in stat_rows
        ]
        return lotteries, draws, stats


class InterestingFactAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        status: InterestingFactStatus | None = None,
        lottery_id: UUID | None = None,
        fact_type: str | None = None,
        limit: int = 50,
    ) -> tuple[StoredFact, ...]:
        statement = select(InterestingFact, Lottery.code, Lottery.name).join(
            Lottery, Lottery.id == InterestingFact.lottery_id
        )
        if status is not None:
            statement = statement.where(InterestingFact.status == status)
        if lottery_id is not None:
            statement = statement.where(InterestingFact.lottery_id == lottery_id)
        if fact_type:
            statement = statement.where(InterestingFact.fact_type == fact_type)
        rows = (
            await self._session.execute(
                statement.order_by(
                    InterestingFact.generation_date.desc(), InterestingFact.score.desc()
                ).limit(limit)
            )
        ).all()
        unique: dict[tuple[UUID, str, str], StoredFact] = {}
        for fact, code, name in rows:
            item = StoredFact(
                fact.id,
                fact.generation_date,
                fact.generated_at,
                fact.lottery_id,
                code,
                name,
                fact.fact_type,
                fact.title,
                fact.description,
                fact.numeric_values,
                fact.score,
                InterestingFactStatus(fact.status),
            )
            key = (item.lottery_id, item.fact_type, item.title.casefold().strip())
            if key not in unique:
                unique[key] = item
        return tuple(
            sorted(
                unique.values(),
                key=lambda item: (item.generation_date, item.score),
                reverse=True,
            )[:limit]
        )

    async def set_status(
        self, fact_id: UUID, status: InterestingFactStatus
    ) -> StoredFact | None:
        fact = await self._session.get(InterestingFact, fact_id, with_for_update=True)
        if fact is None:
            return None
        fact.status = status
        await self._session.flush()
        lottery = await self._session.get(Lottery, fact.lottery_id)
        if lottery is None:
            return None
        return StoredFact(
            fact.id,
            fact.generation_date,
            fact.generated_at,
            fact.lottery_id,
            lottery.code,
            lottery.name,
            fact.fact_type,
            fact.title,
            fact.description,
            fact.numeric_values,
            fact.score,
            InterestingFactStatus(fact.status),
        )
