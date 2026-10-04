"""Bounded, read-only public draw history for the Mini App."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.query_scope import lottery_scope
from k_loto.domain.enums import DrawStatus
from k_loto.domain.lottery_rules import get_lottery_rules
from k_loto.infrastructure.database.models import Draw, JackpotWinEvent, Lottery


@dataclass(frozen=True)
class ArchiveLottery:
    code: str
    name: str


@dataclass(frozen=True)
class ArchiveDraw:
    id: UUID
    lottery_code: str
    lottery_name: str
    draw_number: int
    scheduled_at: datetime
    total_payout: int
    ticket_count: int | None
    winning_numbers: list[int] | None
    primary_numbers_to_pick: int
    secondary_storage_offset: int
    jackpot_amount: int | None


@dataclass(frozen=True)
class ArchivePage:
    items: list[ArchiveDraw]
    lotteries: list[ArchiveLottery]
    next_cursor: UUID | None


def archive_draw(draw: Draw, lottery: Lottery, jackpot: int | None) -> ArchiveDraw:
    snapshot = draw.configuration_snapshot or {}
    rules = get_lottery_rules(str(snapshot.get("ruleset_code", lottery.ruleset_code)))
    bingo = lottery.code == "bingo"
    return ArchiveDraw(
        id=draw.id,
        lottery_code=lottery.code,
        lottery_name=lottery.name,
        draw_number=draw.public_number,
        scheduled_at=draw.scheduled_at,
        total_payout=draw.total_payout,
        ticket_count=None if bingo else draw.ticket_count,
        winning_numbers=None if bingo else draw.winning_numbers,
        primary_numbers_to_pick=rules.display_primary_numbers_to_pick,
        secondary_storage_offset=rules.secondary_storage_offset,
        jackpot_amount=jackpot,
    )


class DrawArchiveService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def page(
        self,
        *,
        lottery_code: str = "",
        jackpots_only: bool = False,
        before: UUID | None = None,
        limit: int = 30,
    ) -> ArchivePage:
        limit = max(1, min(limit, 50))
        statement = (
            select(Draw, Lottery, JackpotWinEvent.jackpot_amount)
            .join(Lottery, Lottery.id == Draw.lottery_id)
            .outerjoin(JackpotWinEvent, JackpotWinEvent.draw_id == Draw.id)
            .where(Draw.status == DrawStatus.COMPLETED, lottery_scope("standard"))
        )
        if lottery_code:
            statement = statement.where(Lottery.code == lottery_code)
        if jackpots_only:
            statement = statement.where(JackpotWinEvent.id.is_not(None))
        if before:
            anchor = (
                await self.session.execute(
                    select(Draw.scheduled_at, Draw.id)
                    .join(Lottery, Lottery.id == Draw.lottery_id)
                    .where(
                        Draw.id == before,
                        Draw.status == DrawStatus.COMPLETED,
                        lottery_scope("standard"),
                    )
                )
            ).first()
            if anchor is None:
                raise ValueError("Недействительная страница архива.")
            statement = statement.where(
                tuple_(Draw.scheduled_at, Draw.id) < tuple_(anchor[0], anchor[1])
            )
        rows = (
            await self.session.execute(
                statement.order_by(Draw.scheduled_at.desc(), Draw.id.desc()).limit(
                    limit + 1
                )
            )
        ).all()
        lotteries = (
            await self.session.execute(
                select(Lottery.code, Lottery.name)
                .where(lottery_scope("standard"))
                .order_by(Lottery.name, Lottery.code)
            )
        ).all()
        return ArchivePage(
            items=[
                archive_draw(draw, lottery, jackpot)
                for draw, lottery, jackpot in rows[:limit]
            ],
            lotteries=[ArchiveLottery(code, name) for code, name in lotteries],
            next_cursor=rows[limit - 1][0].id if len(rows) > limit else None,
        )
