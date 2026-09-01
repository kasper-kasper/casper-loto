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


async def ensure_lottery(
    code: str,
    name: str,
    kind: LotteryKind,
    pick: int,
    maximum: int,
    cutoff: int,
    schedule: dict[str, object],
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
        "ЛСД-лото",
        LotteryKind.WEEKLY,
        5,
        20,
        5,
        {"weekday": "sunday", "draw_time": "20:00"},
    )
    for code, name, slots in (
        ("pll", "ПЛЛ-лото", ["02:22", "13:45"]),
        ("pss", "ПСС-Лото", ["12:00", "20:30"]),
        ("khan", "ХАН-Лото", ["09:00", "18:00"]),
    ):
        await ensure_lottery(
            code,
            name,
            LotteryKind.DAILY,
            4,
            15,
            2,
            {"slots": slots},
        )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
