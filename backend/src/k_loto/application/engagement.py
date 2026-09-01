"""Notification preferences, player inbox and restrained re-engagement."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from k_loto.domain.enums import (
    DrawStatus,
    InAppNotificationType,
    NotificationStatus,
    NotificationType,
)
from k_loto.domain.lotteries import FAST_LOTTERY_CODES, draw_display_name
from k_loto.infrastructure.database.models import (
    Draw,
    Lottery,
    NotificationOutbox,
    Ticket,
    User,
    UserNotification,
    UserNotificationPreference,
)


@dataclass(frozen=True, slots=True)
class EngagementReport:
    invited_user_ids: tuple[UUID, ...]
    telegram_user_ids: tuple[UUID, ...]


class PlayerEngagementService:
    """Invite inactive players at most once per 24 hours."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def run(self, *, now: datetime | None = None) -> EngagementReport:
        timestamp = now or datetime.now(UTC)
        inactivity_before = timestamp - timedelta(hours=24)
        async with self._session_factory() as session, session.begin():
            next_row = (
                await session.execute(
                    select(Draw, Lottery)
                    .join(Lottery, Lottery.id == Draw.lottery_id)
                    .where(
                        Draw.status == DrawStatus.SCHEDULED,
                        Draw.sales_close_at > timestamp,
                        Lottery.is_active.is_(True),
                        Lottery.code.not_in(FAST_LOTTERY_CODES),
                    )
                    .order_by(Draw.scheduled_at, Draw.public_number)
                    .limit(1)
                )
            ).first()
            if next_row is None:
                return EngagementReport((), ())
            draw, lottery = next_row
            rows = (
                await session.execute(
                    select(
                        UserNotificationPreference,
                        User,
                        func.max(Ticket.purchased_at),
                    )
                    .join(User, User.id == UserNotificationPreference.user_id)
                    .outerjoin(Ticket, Ticket.user_id == User.id)
                    .where(User.is_active.is_(True), User.is_admin.is_(False))
                    .group_by(UserNotificationPreference.user_id, User.id)
                )
            ).all()
            invited: list[UUID] = []
            telegram: list[UUID] = []
            lottery_name = draw_display_name(
                lottery.code, lottery.name, draw.scheduled_at
            )
            for preference, user, last_purchase_at in rows:
                last_activity = last_purchase_at or user.created_at
                if last_activity > inactivity_before:
                    continue
                if (
                    preference.last_inactivity_reminder_at is not None
                    and preference.last_inactivity_reminder_at > inactivity_before
                ):
                    continue
                event_suffix = str(int(timestamp.timestamp() // 86_400))
                payload = {
                    "lottery_code": lottery.code,
                    "lottery_name": lottery_name,
                    "draw_number": draw.public_number,
                    "scheduled_at": draw.scheduled_at.isoformat(),
                    "sales_close_at": draw.sales_close_at.isoformat(),
                }
                session.add(
                    UserNotification(
                        id=uuid4(),
                        event_key=f"invite:{user.id}:{event_suffix}",
                        user_id=user.id,
                        type=InAppNotificationType.DRAW_INVITATION,
                        title="Ближайший тираж уже открыт",
                        body=(
                            f"{lottery_name}, тираж №{draw.public_number:04d}. "
                            "Можно выбрать числа заранее."
                        ),
                        payload=payload,
                        created_at=timestamp,
                    )
                )
                invited.append(user.id)
                if (
                    preference.telegram_enabled
                    and preference.inactivity_reminders_enabled
                    and user.telegram_id is not None
                ):
                    session.add(
                        NotificationOutbox(
                            id=uuid4(),
                            event_key=f"inactive:{user.id}:{event_suffix}",
                            user_id=user.id,
                            type=NotificationType.INACTIVITY_REMINDER,
                            status=NotificationStatus.PENDING,
                            payload=payload,
                            attempts=0,
                            available_at=timestamp,
                        )
                    )
                    telegram.append(user.id)
                preference.last_inactivity_reminder_at = timestamp
        return EngagementReport(tuple(invited), tuple(telegram))
