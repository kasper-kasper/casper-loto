"""One private, ledger-based owner digest per complete Moscow day and epoch."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import Integer, case, func, literal, select, text, union_all
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from k_loto.application.economy import ECONOMY_LOCK, control_state
from k_loto.application.economy_reporting import EconomyReportService
from k_loto.application.weekly import KASPER_FUND_ID
from k_loto.domain.enums import (
    DrawStatus,
    NotificationStatus,
    NotificationType,
    TicketSource,
    TicketStatus,
)
from k_loto.domain.lotteries import FAST_LOTTERY_CODES
from k_loto.domain.schedules import MOSCOW
from k_loto.infrastructure.database.models import (
    Balance,
    Draw,
    InstantTicket,
    JackpotAccount,
    KasperFundAccount,
    Lottery,
    NotificationOutbox,
    Ticket,
    User,
)

SUMMARY_KIND = "owner_daily_economy"


def ticket_activity_query(*, start: datetime, end: datetime, epoch: int) -> Select[Any]:
    """One row per purchased ticket, including Dual only once; gifts stay separate.

    Purchases are gross confirmed purchases, matching the ledger's purchase flow.
    Later refunds are reported separately, never erased from business history.
    """
    draw_epoch = func.coalesce(
        Draw.configuration_snapshot["economy_epoch"].astext, "1"
    ).cast(Integer)
    tickets = union_all(
        select(
            Ticket.user_id.label("user_id"),
            case(
                (Ticket.source == TicketSource.GIFT, "gift"),
                (Lottery.code.in_(FAST_LOTTERY_CODES), "fast"),
                else_="regular",
            ).label("kind"),
            (Ticket.status == TicketStatus.REFUNDED).label("refunded"),
        )
        .join(Draw, Draw.id == Ticket.draw_id)
        .join(Lottery, Lottery.id == Ticket.lottery_id)
        .where(
            Ticket.purchased_at >= start,
            Ticket.purchased_at < end,
            draw_epoch == epoch,
        ),
        select(
            InstantTicket.user_id,
            literal("instant").label("kind"),
            literal(False).label("refunded"),
        ).where(InstantTicket.purchased_at >= start, InstantTicket.purchased_at < end),
    ).subquery()
    return select(
        *(
            func.count().filter(tickets.c.kind == kind).label(kind)
            for kind in ("regular", "fast", "instant", "gift")
        ),
        func.count()
        .filter(tickets.c.refunded, tickets.c.kind != "gift")
        .label("refunded"),
        func.count(
            func.distinct(case((tickets.c.kind != "gift", tickets.c.user_id)))
        ).label("buyers"),
    ).select_from(tickets)


def due_report_day(now: datetime) -> date | None:
    local = now.astimezone(MOSCOW)
    return local.date() - timedelta(days=1) if local.time() >= time(0, 5) else None


def digest_metrics(
    report: dict[str, Any],
    *,
    regular: int,
    instant: int,
    fund: int,
    pending: int,
    fast: int = 0,
    gifts: int = 0,
    refunded_tickets: int = 0,
    buyers: int = 0,
    new_players: int = 0,
    player_balances: int = 0,
    jackpots: int = 0,
) -> dict[str, Any]:
    day = report["days"][-1]
    complete = [x for x in report["days"] if x["included"] and not x["partial"]]
    net_expense = -sum(x["fund_net"] for x in complete)
    runway = fund * len(complete) // net_expense if net_expense > 0 else None
    attention = (
        "unresolved_draws"
        if pending
        else "fund_empty"
        if fund == 0
        else "fund_less_than_day"
        if runway == 0
        else None
    )
    return {
        "kind": SUMMARY_KIND,
        "economy_epoch": report["epoch"],
        "report_day": str(report["selected_day"]),
        "partial": day["partial"],
        "regular_tickets": regular,
        "fast_tickets": fast,
        "instant_tickets": instant,
        "total_tickets": regular + fast + instant,
        "gift_tickets": gifts,
        "refunded_tickets": refunded_tickets,
        "buyers": buyers,
        "new_players": new_players,
        "purchases": day["purchases"],
        "prizes": day["prizes"],
        "refunds": day["refunds"],
        "other_credit": day["other_credit"] - day["achievement_rewards"],
        "achievement_rewards": day["achievement_rewards"],
        "admin_net": day["admin_credit"] - day["admin_debit"],
        "game_net": day["purchases"] - day["prizes"] - day["refunds"],
        "issued": day["issued"],
        "burned": day["burned"],
        "supply_net": day["supply_net"],
        "player_net": day["player_net"],
        "fund_balance": fund,
        "fund_net": day["fund_net"],
        "fund_runway_days": runway,
        "fund_daily_expense": (net_expense + len(complete) - 1) // len(complete)
        if net_expense > 0
        else 0,
        "trend_days": len(complete),
        "player_balances": player_balances,
        "jackpots": jackpots,
        "pending_draws": pending,
        "attention": attention,
    }


class OwnerEconomySummaryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def prepare(self, *, owner_telegram_id: int | None, now: datetime) -> bool:
        day = due_report_day(now)
        if owner_telegram_id is None or day is None:
            return False
        async with self.session.begin():
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock_shared(:key)"), {"key": ECONOMY_LOCK}
            )
            control = await control_state(self.session)
            if control.paused:
                return False
            end = datetime.combine(
                day + timedelta(days=1), time.min, MOSCOW
            ).astimezone(UTC)
            if control.epoch_started_at and end <= control.epoch_started_at:
                return False
            key = f"owner-economy:{control.epoch}:{day}:{owner_telegram_id}"
            existing = await self.session.scalar(
                select(NotificationOutbox)
                .where(NotificationOutbox.event_key == key)
                .with_for_update()
            )
            if existing is not None:
                if (
                    existing.status != NotificationStatus.CANCELLED
                    or existing.last_error != "owner_report_recipient_changed"
                    or existing.sent_at is not None
                ):
                    return False
                owner = await self.session.scalar(
                    select(User.id).where(
                        User.telegram_id == owner_telegram_id, User.is_active.is_(True)
                    )
                )
                if owner is None or existing.user_id != owner:
                    return False
                existing.status = NotificationStatus.PENDING
                existing.available_at = now
                existing.locked_at = None
                existing.last_error = None
                return True
            owner = await self.session.scalar(
                select(User.id).where(
                    User.telegram_id == owner_telegram_id, User.is_active.is_(True)
                )
            )
            if owner is None:
                return False
            self.session.info["economy_scope"] = (control.epoch, "current")
            self.session.info["economy_started_at"] = control.epoch_started_at
            report = await EconomyReportService(self.session).daily(
                through=day, now=now
            )
            start = max(
                end - timedelta(days=1),
                control.epoch_started_at or end - timedelta(days=1),
            )
            draw_epoch = func.coalesce(
                Draw.configuration_snapshot["economy_epoch"].astext, "1"
            ).cast(Integer)
            activity = (
                (
                    await self.session.execute(
                        ticket_activity_query(start=start, end=end, epoch=control.epoch)
                    )
                )
                .mappings()
                .one()
            )
            new_players = int(
                await self.session.scalar(
                    select(func.count(User.id)).where(
                        User.created_at >= start,
                        User.created_at < end,
                        User.telegram_id.is_not(None),
                    )
                )
                or 0
            )
            pending = int(
                await self.session.scalar(
                    select(func.count(Draw.id)).where(
                        Draw.scheduled_at >= start,
                        Draw.scheduled_at < end,
                        draw_epoch == control.epoch,
                        Draw.status.not_in(
                            (DrawStatus.COMPLETED, DrawStatus.CANCELLED)
                        ),
                    )
                )
                or 0
            )
            fund = await self.session.scalar(
                select(KasperFundAccount.balance).where(
                    KasperFundAccount.id == KASPER_FUND_ID
                )
            )
            if fund is None:
                raise RuntimeError("Kasper Fund account is missing.")
            player_balances = int(
                await self.session.scalar(select(func.sum(Balance.amount))) or 0
            )
            jackpots = int(
                await self.session.scalar(select(func.sum(JackpotAccount.balance))) or 0
            )
            payload = digest_metrics(
                report,
                regular=int(activity["regular"]),
                fast=int(activity["fast"]),
                instant=int(activity["instant"]),
                gifts=int(activity["gift"]),
                refunded_tickets=int(activity["refunded"]),
                buyers=int(activity["buyers"]),
                new_players=new_players,
                player_balances=player_balances,
                jackpots=jackpots,
                fund=int(fund),
                pending=pending,
            )
            payload["prepared_at"] = now.isoformat()
            result = await self.session.scalar(
                insert(NotificationOutbox)
                .values(
                    id=uuid4(),
                    event_key=key,
                    user_id=owner,
                    type=NotificationType.SYSTEM_ALERT,
                    status=NotificationStatus.PENDING,
                    payload=payload,
                    attempts=0,
                    available_at=now,
                )
                .on_conflict_do_nothing(index_elements=[NotificationOutbox.event_key])
                .returning(NotificationOutbox.id)
            )
            return result is not None
