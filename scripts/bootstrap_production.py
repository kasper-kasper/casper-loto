"""Idempotently create production lottery entities and their zero-CAS accounts."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from k_loto.application.scheduler import DrawScheduleService
from k_loto.domain.enums import LotteryKind
from k_loto.infrastructure.database.models import (
    DistributionFund,
    JackpotAccount,
    Lottery,
    LotteryReserve,
)
from k_loto.infrastructure.database.session import engine, session_factory

FAST_SALES_CUTOFF_SECONDS = 8
FAST_LOTTERY_FORMATS = (
    ("flash", "FLASH", "00:00", "fast_3_16", 3, 16),
    ("shadow", "CODE", "00:03", "code_4_digits", 4, 9),
    ("pulse", "PULSE", "00:06", "pulse_2_10_2_5", 4, 15),
)


def fast_schedule(anchor_time: str) -> dict[str, object]:
    """Return the canonical Fast schedule without losing its short cutoff."""
    return {
        "type": "interval",
        "interval_minutes": 9,
        "anchor_time": anchor_time,
        "future_draw_count": 2,
        "category": "fast",
        "live_enabled": True,
        "sales_cutoff_seconds": FAST_SALES_CUTOFF_SECONDS,
    }


async def ensure_lottery(
    code: str,
    name: str,
    kind: LotteryKind,
    pick: int,
    maximum: int,
    cutoff: int,
    schedule: dict[str, object],
    ruleset_code: str,
) -> None:
    async with session_factory() as session, session.begin():
        lottery = await session.scalar(
            select(Lottery).where(Lottery.code == code).with_for_update()
        )
        created = lottery is None
        if lottery is None:
            lottery = Lottery(
                id=uuid4(),
                code=code,
                name=name,
                kind=kind,
                ruleset_code=ruleset_code,
                numbers_to_pick=pick,
                max_number=maximum,
                ticket_price=None,
                timezone="Europe/Moscow",
                schedule=schedule,
                sales_cutoff_minutes=cutoff,
                is_active=True,
                next_draw_number=1,
                next_ticket_number=1,
            )
            session.add(lottery)
            await session.flush()
        lottery.sales_cutoff_minutes = cutoff
        lottery.name = name
        lottery.schedule = schedule
        lottery.ruleset_code = ruleset_code
        lottery.numbers_to_pick = pick
        lottery.max_number = maximum
        if created:
            lottery.is_active = True
        for model in (JackpotAccount, DistributionFund, LotteryReserve):
            account = await session.scalar(
                select(model).where(model.lottery_id == lottery.id)
            )
            if account is None:
                values = {"id": uuid4(), "lottery_id": lottery.id, "balance": 0}
                if model is JackpotAccount:
                    values["base_amount"] = 0
                session.add(model(**values))
        lottery_id = lottery.id
        is_active = lottery.is_active
    if is_active:
        async with session_factory() as session:
            await DrawScheduleService(session).ensure_next_draw(
                lottery_id, reference=datetime.now(UTC)
            )


async def main() -> None:
    await ensure_lottery(
        "weekly",
        "Kasper Grand",
        LotteryKind.WEEKLY,
        7,
        40,
        5,
        {"weekday": "sunday", "draw_time": "20:00"},
        "weekly_grand_5_35_2_5",
    )
    for code, name, slots in (
        ("pll", "ПЛЛ-лото", ["02:22", "13:45"]),
        ("pss", "ПСС-Лото", ["12:00", "20:30"]),
    ):
        await ensure_lottery(
            code,
            name,
            LotteryKind.DAILY,
            4,
            15,
            2,
            {"slots": slots},
            "daily_4_15",
        )
    await ensure_lottery(
        "khan",
        "6 из 36",
        LotteryKind.DAILY,
        6,
        36,
        2,
        {"slots": ["09:00", "18:00"]},
        "classic_6_36",
    )
    for code, name, anchor_time, ruleset_code, pick, maximum in FAST_LOTTERY_FORMATS:
        await ensure_lottery(
            code,
            name,
            LotteryKind.DAILY,
            pick,
            maximum,
            1,
            fast_schedule(anchor_time),
            ruleset_code,
        )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
