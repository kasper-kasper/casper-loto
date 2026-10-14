"""Distribution designation and its dedicated immediate text announcement queue."""

import asyncio
import re
from collections import Counter
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from k_loto.core.config import get_settings
from k_loto.domain.enums import AuditAction, DrawStatus, TicketStatus
from k_loto.domain.schedules import next_draw_at, sales_close_at
from k_loto.infrastructure.database.models import (
    AdminAuditLog,
    DistributionAnnouncement,
    Draw,
    JackpotAccount,
    JackpotWinEvent,
    Lottery,
    Ticket,
)

MOSCOW = ZoneInfo("Europe/Moscow")


def projected_id(lottery_id: UUID, at: datetime) -> UUID:
    return uuid5(
        NAMESPACE_URL, f"distribution:{lottery_id}:{at.astimezone(UTC).isoformat()}"
    )


def announcement_text(
    name: str, code: str, number: int, at: datetime, jackpot: int
) -> str:
    when = at.astimezone(MOSCOW).strftime("%d.%m.%Y в %H:%M МСК")
    title = (
        f"Большой день для {name}!",
        f"Джекпот {name} найдёт своих победителей!",
        f"Особый тираж в {name}!",
    )[number % 3]
    hashtag = re.sub(r"[^\w]", "", name, flags=re.UNICODE)
    return (
        f"{title}\n\n{when} проведём распределительный тираж №{number}.\n"
        f"Полностью распределим весь джекпот. Сейчас он составляет {jackpot:,} CAS.\n\n"
        "Если полную комбинацию никто не угадает, джекпот поделят билеты ближайшей "
        "призовой категории с победителями. Если все категории пустые — все купленные "
        "билеты этого тиража. Обычные выигрыши сохраняются.\n\n"
        "Уже купили билет? Он тоже участвует — ничего делать не нужно.\n"
        "Если билетов не будет, джекпот переносится дальше.\n\n"
        f"#CasperLotto #{hashtag or code} #РаспределительныйТираж #Джекпот"
    ).replace(",", " ")


def validate_assignment(draw: Draw, lottery: Lottery, now: datetime) -> None:
    if (
        lottery.code in {"dual", "kasper-live", "aurora", "vault"}
        or not lottery.is_active
    ):
        raise ValueError("Эта лотерея не участвует в распределительных тиражах.")
    if (
        draw.status != DrawStatus.SCHEDULED
        or now >= draw.sales_close_at
        or now >= draw.scheduled_at
    ):
        raise ValueError("Назначение возможно только до окончания продаж.")


def result_text(
    lottery: Lottery, draw: Draw, prizes: Counter[int], jackpot_paid: int
) -> str:
    winning = sum(count for amount, count in prizes.items() if amount > 0)

    def amount(value: int) -> str:
        return f"{value:,}".replace(",", " ")

    when = draw.scheduled_at.astimezone(MOSCOW).strftime("%d.%m.%Y · %H:%M МСК")
    lines = [
        f"Распределительный тираж №{draw.public_number} завершён · {lottery.name}",
        when,
        "",
        f"Из джекпота выплачено: {amount(jackpot_paid)} CAS.",
        f"Выигрышных билетов: {amount(winning)}.",
        f"Всего выигрышей: {amount(draw.total_payout)} CAS.",
    ]
    tiers = sorted(
        ((value, count) for value, count in prizes.items() if value > 0), reverse=True
    )
    if tiers:
        lines.extend(["", "Выплаты по билетам:"])
        lines.extend(
            f"• {amount(count)} шт. — по {amount(value)} CAS"
            for value, count in tiers[:20]
        )
        if len(tiers) > 20:
            lines.append(
                f"• Остальные {amount(sum(c for _, c in tiers[20:]))} "
                "выигрышных билетов "
                f"— всего {amount(sum(v * c for v, c in tiers[20:]))} CAS"
            )
        lines.extend(["", "Все выигрыши уже зачислены."])
    elif not draw.ticket_count:
        lines.extend(["", "Билетов не было — джекпот переносится в следующий тираж."])
    else:
        lines.extend(["", "Выигрышных билетов нет."])
    lines.extend(
        [
            f"Джекпот после тиража: {amount(draw.jackpot_closing or 0)} CAS.",
            "",
            f"#CasperLotto #{re.sub(r'\W', '', lottery.name)} "
            "#РаспределительныйТираж #Результаты",
        ]
    )
    return "\n".join(lines)


def queue_result(
    session: AsyncSession,
    lottery: Lottery,
    draw: Draw,
    prizes: Counter[int],
    jackpot_paid: int,
    now: datetime,
) -> None:
    session.add(
        DistributionAnnouncement(
            id=uuid4(),
            draw_id=draw.id,
            kind="result",
            text=result_text(lottery, draw, prizes, jackpot_paid),
            state="queued",
            created_at=now,
        )
    )


async def recover_results(
    factory: async_sessionmaker[AsyncSession], *, now: datetime
) -> None:
    """Recover fresh completed receipts without editing any historical draw."""
    async with factory() as session, session.begin():
        rows = (
            await session.execute(
                select(Draw, Lottery)
                .join(Lottery, Lottery.id == Draw.lottery_id)
                .outerjoin(
                    DistributionAnnouncement,
                    and_(
                        DistributionAnnouncement.draw_id == Draw.id,
                        DistributionAnnouncement.kind == "result",
                    ),
                )
                .where(
                    Draw.status == DrawStatus.COMPLETED,
                    Draw.is_distribution.is_(True),
                    Draw.executed_at > now - timedelta(hours=24),
                    Draw.executed_at <= now,
                    DistributionAnnouncement.id.is_(None),
                    Lottery.code != "dual",
                )
                .order_by(Draw.scheduled_at, Draw.id)
                .limit(100)
                .with_for_update(of=Draw, skip_locked=True)
            )
        ).all()
        for draw, lottery in rows:
            payouts = (
                await session.scalars(
                    select(Ticket.prize_amount).where(
                        Ticket.draw_id == draw.id, Ticket.status == TicketStatus.SETTLED
                    )
                )
            ).all()
            won = await session.scalar(
                select(JackpotWinEvent.jackpot_amount).where(
                    JackpotWinEvent.draw_id == draw.id
                )
            )
            queue_result(
                session,
                lottery,
                draw,
                Counter(payouts),
                draw.distributed_amount or won or 0,
                now,
            )


class DistributionDrawService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(self, lottery_id: UUID, day: date) -> list[dict[str, Any]]:
        start = datetime.combine(day, time.min, MOSCOW).astimezone(UTC)
        rows = (
            await self.session.execute(
                select(Draw, Lottery, JackpotAccount.balance, DistributionAnnouncement)
                .join(Lottery, Lottery.id == Draw.lottery_id)
                .join(JackpotAccount, JackpotAccount.lottery_id == Lottery.id)
                .outerjoin(
                    DistributionAnnouncement,
                    and_(
                        DistributionAnnouncement.draw_id == Draw.id,
                        DistributionAnnouncement.kind == "schedule",
                    ),
                )
                .where(
                    Draw.lottery_id == lottery_id,
                    Lottery.code != "dual",
                    Lottery.is_active.is_(True),
                    Draw.scheduled_at >= start,
                    Draw.scheduled_at < start + timedelta(days=1),
                )
                .order_by(Draw.scheduled_at)
            )
        ).all()
        result = [
            self._view(draw, lottery, jackpot, post)
            for draw, lottery, jackpot, post in rows
        ]
        lottery = await self.session.get(Lottery, lottery_id)
        if (
            lottery is None
            or not lottery.is_active
            or lottery.code in {"dual", "kasper-live", "aurora", "vault"}
        ):
            return []
        latest = await self.session.scalar(
            select(Draw)
            .where(Draw.lottery_id == lottery_id)
            .order_by(Draw.scheduled_at.desc())
            .limit(1)
        )
        jackpot = await self.session.scalar(
            select(JackpotAccount.balance).where(
                JackpotAccount.lottery_id == lottery_id
            )
        )
        if latest is None or jackpot is None:
            return result
        at, number = latest.scheduled_at, lottery.next_draw_number
        end = start + timedelta(days=1)
        while at < end:
            at = next_draw_at(lottery.kind, at, lottery.schedule)
            if at >= end:
                break
            if at >= start:
                projected = Draw(
                    id=projected_id(lottery_id, at),
                    lottery_id=lottery_id,
                    public_number=number,
                    scheduled_at=at,
                    sales_close_at=sales_close_at(
                        lottery.kind, at, lottery.sales_cutoff_minutes, lottery.schedule
                    ),
                    status=DrawStatus.SCHEDULED,
                    ticket_count=0,
                    is_distribution=False,
                )
                result.append(self._view(projected, lottery, jackpot, None))
            number += 1
        return result

    async def prepare(self, lottery_id: UUID, at: datetime, identifier: UUID) -> UUID:
        """Materialize the official sequence, without skipping intermediate draws.

        The lottery lock matches scheduler preparation; assignment uses a separate
        transaction in draw-first order, matching settlement and existing purchases.
        """
        from k_loto.application.weekly import draw_configuration_snapshot

        if at.tzinfo is None or identifier != projected_id(lottery_id, at):
            raise ValueError("Некорректный тираж календаря.")
        async with self.session.begin():
            lottery = await self.session.scalar(
                select(Lottery).where(Lottery.id == lottery_id).with_for_update()
            )
            if lottery is None:
                raise LookupError("Лотерея не найдена.")
            if (
                lottery.code in {"dual", "kasper-live", "aurora", "vault"}
                or not lottery.is_active
            ):
                raise ValueError(
                    "Эта лотерея не участвует в распределительных тиражах."
                )
            existing = await self.session.scalar(
                select(Draw).where(
                    Draw.lottery_id == lottery_id, Draw.scheduled_at == at
                )
            )
            if existing is not None:
                return existing.id
            latest = await self.session.scalar(
                select(Draw)
                .where(Draw.lottery_id == lottery_id)
                .order_by(Draw.scheduled_at.desc())
                .limit(1)
            )
            jackpot = await self.session.scalar(
                select(JackpotAccount).where(JackpotAccount.lottery_id == lottery_id)
            )
            if latest is None or jackpot is None or at <= latest.scheduled_at:
                raise ValueError("Обновите календарь тиражей.")
            probe = next_draw_at(lottery.kind, latest.scheduled_at, lottery.schedule)
            timestamps = []
            while probe <= at:
                timestamps.append(probe)
                if probe == at:
                    break
                probe = next_draw_at(lottery.kind, probe, lottery.schedule)
            if not timestamps or timestamps[-1] != at:
                raise ValueError("В это время по расписанию нет тиража.")
            if datetime.now(UTC) >= sales_close_at(
                lottery.kind, at, lottery.sales_cutoff_minutes, lottery.schedule
            ):
                raise ValueError("Назначение возможно только до окончания продаж.")
            for stamp in timestamps:
                draw = Draw(
                    id=projected_id(lottery_id, stamp),
                    lottery_id=lottery_id,
                    public_number=lottery.next_draw_number,
                    status=DrawStatus.SCHEDULED,
                    scheduled_at=stamp,
                    sales_close_at=sales_close_at(
                        lottery.kind,
                        stamp,
                        lottery.sales_cutoff_minutes,
                        lottery.schedule,
                    ),
                    correlation_id=uuid4(),
                    ticket_count=0,
                    total_sales=0,
                    total_payout=0,
                    reserve_used=0,
                    kasper_fund_used=0,
                    configuration_snapshot=draw_configuration_snapshot(
                        lottery, jackpot.base_amount
                    ),
                )
                lottery.next_draw_number += 1
                self.session.add(draw)
                if lottery.code == "bingo":
                    from k_loto.application.bingo import ensure_pool

                    await ensure_pool(self.session, lottery, draw)
        return identifier

    @staticmethod
    def _view(
        draw: Draw,
        lottery: Lottery,
        jackpot: int,
        announcement: DistributionAnnouncement | None,
    ) -> dict[str, Any]:
        return dict(
            id=str(draw.id),
            lottery_id=str(lottery.id),
            lottery_name=lottery.name,
            number=draw.public_number,
            scheduled_at=draw.scheduled_at,
            sales_close_at=draw.sales_close_at,
            jackpot=jackpot,
            ticket_count=draw.ticket_count,
            is_distribution=bool(draw.is_distribution),
            status=draw.status.value,
            announcement_state=announcement.state if announcement else None,
            post=announcement.text
            if announcement
            else announcement_text(
                lottery.name,
                lottery.code,
                draw.public_number,
                draw.scheduled_at,
                jackpot,
            ),
        )

    async def assign(
        self, draw_id: UUID, admin_id: UUID, *, now: datetime | None = None
    ) -> dict[str, Any]:
        async with self.session.begin():
            draw = await self.session.scalar(
                select(Draw).where(Draw.id == draw_id).with_for_update()
            )
            if draw is None:
                raise LookupError("Тираж не найден.")
            lottery = await self.session.get(Lottery, draw.lottery_id)
            if lottery is None:
                raise LookupError("Лотерея не найдена.")
            if lottery.code in {"dual", "kasper-live", "aurora", "vault"}:
                raise ValueError(
                    "Эта лотерея не участвует в распределительных тиражах."
                )
            jackpot = await self.session.scalar(
                select(JackpotAccount.balance).where(
                    JackpotAccount.lottery_id == lottery.id
                )
            )
            if jackpot is None:
                raise ValueError("Счёт джекпота отсутствует.")
            announcement = await self.session.scalar(
                select(DistributionAnnouncement).where(
                    DistributionAnnouncement.draw_id == draw.id,
                    DistributionAnnouncement.kind == "schedule",
                )
            )
            if draw.is_distribution:
                return self._view(draw, lottery, jackpot, announcement)
            timestamp = now or datetime.now(UTC)
            validate_assignment(draw, lottery, timestamp)
            settings = get_settings()
            if not settings.lottery_bot_token or not settings.publication_channel:
                raise ValueError("Для назначения настройте бота и канал публикаций.")
            draw.is_distribution = True
            announcement = DistributionAnnouncement(
                id=uuid4(),
                draw_id=draw.id,
                kind="schedule",
                text=announcement_text(
                    lottery.name,
                    lottery.code,
                    draw.public_number,
                    draw.scheduled_at,
                    jackpot,
                ),
                state="queued",
            )
            self.session.add(announcement)
            self.session.add(
                AdminAuditLog(
                    id=uuid4(),
                    admin_user_id=admin_id,
                    action=AuditAction.UPDATE,
                    entity_type="distribution_draw",
                    entity_id=draw.id,
                    old_values={"is_distribution": False},
                    new_values={
                        "is_distribution": True,
                        "scheduled_at": draw.scheduled_at.isoformat(),
                    },
                    reason="Distribution designation; existing tickets participate",
                    created_at=timestamp,
                )
            )
            return self._view(draw, lottery, jackpot, announcement)


async def deliver_distribution(
    factory: async_sessionmaker[AsyncSession], bot: Any, *, now: datetime
) -> str:
    async with factory() as session, session.begin():
        # Telegram has no idempotency key for sendMessage. A crashed sender may
        # have already published; record uncertainty rather than sending twice.
        await session.execute(
            update(DistributionAnnouncement)
            .where(
                DistributionAnnouncement.state == "sending",
                DistributionAnnouncement.retry_after <= now,
            )
            .values(state="uncertain", error_type="InterruptedDelivery")
        )
        row = await session.scalar(
            select(DistributionAnnouncement)
            .where(
                DistributionAnnouncement.state == "queued",
                or_(
                    DistributionAnnouncement.retry_after.is_(None),
                    DistributionAnnouncement.retry_after <= now,
                ),
            )
            .order_by(DistributionAnnouncement.created_at, DistributionAnnouncement.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if row is None:
            return "empty"
        draw = await session.get(Draw, row.draw_id)
        if draw is None or (row.kind != "result" and draw.scheduled_at <= now):
            row.state = "expired"
            return "expired"
        row.state = "sending"
        row.retry_after = now + timedelta(minutes=1)
        identifier, text = row.id, row.text
    try:
        async with asyncio.timeout(15):
            message = await bot.send_message(
                get_settings().publication_channel, text=text, parse_mode=None
            )
    except TelegramRetryAfter as error:
        async with factory() as session, session.begin():
            row = await session.get(
                DistributionAnnouncement, identifier, with_for_update=True
            )
            assert row is not None
            row.state = "queued"
            row.retry_after = datetime.now(UTC) + timedelta(seconds=error.retry_after)
        return "throttled"
    except Exception as error:
        async with factory() as session, session.begin():
            row = await session.get(
                DistributionAnnouncement, identifier, with_for_update=True
            )
            assert row is not None
            row.state = (
                "failed"
                if isinstance(error, (TelegramBadRequest, TelegramForbiddenError))
                else "uncertain"
            )
            row.error_type = type(error).__name__
        return "uncertain"
    async with factory() as session, session.begin():
        row = await session.get(
            DistributionAnnouncement, identifier, with_for_update=True
        )
        assert row is not None
        row.state, row.message_id, row.sent_at = (
            "sent",
            message.message_id,
            datetime.now(UTC),
        )
    return "sent"


async def drain_distribution(factory: async_sessionmaker[AsyncSession]) -> None:
    settings = get_settings()
    if not settings.lottery_bot_token or not settings.publication_channel:
        return
    await recover_results(factory, now=datetime.now(UTC))
    bot = Bot(settings.lottery_bot_token.get_secret_value())
    try:
        while await deliver_distribution(factory, bot, now=datetime.now(UTC)) in {
            "sent",
            "expired",
        }:
            pass
    finally:
        await bot.session.close()
