"""Step 4 regressions on a disposable schema clone; never real Telegram I/O."""

import asyncio
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError

from k_loto.application.engagement import PlayerEngagementService
from k_loto.application.notifications import NotificationDispatcher
from k_loto.application.publication_automation import deliver_one
from k_loto.application.publication_events import PublicationEventService
from k_loto.application.publications import PublicationService
from k_loto.application.scheduler import DrawRecoveryService, DrawScheduleService
from k_loto.domain.enums import (
    AuditAction,
    DrawStatus,
    LotteryKind,
    NotificationStatus,
    NotificationType,
)
from k_loto.infrastructure.database.models import (
    AdminAuditLog,
    Draw,
    InstantTicket,
    JackpotAccount,
    Lottery,
    NotificationOutbox,
    Publication,
    Ticket,
    User,
    UserNotificationPreference,
)
from k_loto.infrastructure.database.session import engine, session_factory
from k_loto.infrastructure.notification_repository import SqlNotificationRepository
from k_loto.infrastructure.telegram_messages import BotNotificationFormatter


async def rejected(statement):
    try:
        async with session_factory() as session, session.begin():
            await session.execute(statement)
    except DBAPIError:
        return
    raise AssertionError("Database accepted a forbidden history/configuration mutation")


async def main():
    if not str(engine.url.database).startswith("k_loto_audit_stage1_"):
        raise RuntimeError("Disposable audit database required")
    now = datetime.now(UTC)
    async with session_factory() as session, session.begin():
        # Earlier financial checks have created their own synthetic history.
        user = User(
            id=uuid4(),
            display_name="Delivery smoke",
            telegram_id=99111,
            created_at=now - timedelta(days=3),
            is_active=True,
            is_admin=False,
        )
        session.add(user)
        await session.flush()
        session.add(UserNotificationPreference(user_id=user.id, telegram_enabled=True))
        instant = InstantTicket(
            id=uuid4(),
            user_id=user.id,
            symbols=[1, 2, 3],
            purchase_price=2000,
            prize_amount=0,
            odds_version="v1",
        )
        audit = AdminAuditLog(
            id=uuid4(),
            admin_user_id=user.id,
            action=AuditAction.CREATE,
            entity_type="SMOKE",
            reason="Synthetic fixture",
        )
        session.add_all([instant, audit])
        dual = await session.scalar(select(Lottery).where(Lottery.code == "dual"))
        first = Draw(
            id=uuid4(),
            lottery_id=dual.id,
            public_number=100,
            scheduled_at=now + timedelta(days=7),
            sales_close_at=now + timedelta(days=6),
            correlation_id=uuid4(),
            status=DrawStatus.SCHEDULED,
        )
        second = Draw(
            id=uuid4(),
            lottery_id=dual.id,
            public_number=101,
            scheduled_at=first.scheduled_at + timedelta(hours=7),
            sales_close_at=first.sales_close_at,
            correlation_id=uuid4(),
            status=DrawStatus.SCHEDULED,
        )
        session.add_all([first, second])
        await session.flush()
        ticket = Ticket(
            id=uuid4(),
            lottery_id=dual.id,
            draw_id=first.id,
            second_draw_id=second.id,
            user_id=user.id,
            public_number=100,
            numbers=[1, 2, 13, 14],
            purchase_price=20000,
        )
        session.add(ticket)
    for model, identifier in ((InstantTicket, instant.id), (AdminAuditLog, audit.id)):
        field = "prize_amount" if model is InstantTicket else "reason"
        value = 1 if model is InstantTicket else "rewritten"
        await rejected(
            update(model).where(model.id == identifier).values(**{field: value})
        )
        await rejected(delete(model).where(model.id == identifier))
    await rejected(
        update(Ticket).where(Ticket.id == ticket.id).values(second_draw_id=None)
    )
    async with session_factory() as session, session.begin():
        await session.execute(
            update(Ticket).where(Ticket.id == ticket.id).values(dual_night_matches=1)
        )
    await rejected(
        update(Ticket).where(Ticket.id == ticket.id).values(dual_night_matches=2)
    )
    await rejected(update(Lottery).where(Lottery.id == dual.id).values(ticket_price=1))
    await rejected(
        update(Lottery).where(Lottery.id == dual.id).values(ticket_price=None)
    )
    await rejected(
        update(JackpotAccount)
        .where(JackpotAccount.lottery_id == dual.id)
        .values(balance=1)
    )
    await rejected(
        update(JackpotAccount)
        .where(JackpotAccount.lottery_id == dual.id)
        .values(base_amount=1)
    )
    print("immutable instant/audit, Dual identity/results/configuration: PASS")

    repository = SqlNotificationRepository(session_factory)
    stale_id, live_id = uuid4(), uuid4()
    async with session_factory() as session, session.begin():
        session.add_all(
            [
                NotificationOutbox(
                    id=stale_id,
                    user_id=user.id,
                    type=NotificationType.DELIVERY_TEST,
                    event_key=f"stale:{stale_id}",
                    payload={},
                    status=NotificationStatus.PROCESSING,
                    attempts=1,
                    locked_at=now - timedelta(minutes=6),
                ),
                NotificationOutbox(
                    id=live_id,
                    user_id=user.id,
                    type=NotificationType.DELIVERY_TEST,
                    event_key=f"live:{live_id}",
                    payload={},
                    available_at=now,
                ),
            ]
        )
    claims = await asyncio.gather(
        repository.claim_next(now), repository.claim_next(now)
    )
    claim = next(item for item in claims if item is not None)
    assert (
        len([item for item in claims if item is not None]) == 1 and claim.id == live_id
    )
    async with session_factory() as session:
        assert (
            await session.get(NotificationOutbox, stale_id)
        ).status == NotificationStatus.UNCERTAIN
    await repository.mark_failed(
        claim.id, now, "telegram_rate_limited", attempt=claim.attempts, retry_after=120
    )
    assert await repository.claim_next(now + timedelta(seconds=119)) is None
    retry = await repository.claim_next(now + timedelta(seconds=121))
    assert retry.attempts == 2
    await repository.mark_sent(claim.id, now, attempt=1)
    async with session_factory() as session:
        assert (
            await session.get(NotificationOutbox, live_id)
        ).status == NotificationStatus.PROCESSING
    await repository.mark_uncertain(retry.id, now, attempt=retry.attempts)
    assert await repository.claim_next(now + timedelta(days=1)) is None
    revoked_id = uuid4()
    async with session_factory() as session, session.begin():
        preference = await session.get(UserNotificationPreference, user.id)
        preference.telegram_enabled = False
        session.add(
            NotificationOutbox(
                id=revoked_id,
                user_id=user.id,
                type=NotificationType.JACKPOT_WIN,
                event_key=f"revoked:{revoked_id}",
                payload={},
                available_at=now,
            )
        )

    class NeverSend:
        async def send(self, notification, text):
            raise AssertionError("Revoked consent was ignored")

    await NotificationDispatcher(
        repository, NeverSend(), BotNotificationFormatter()
    ).process_one(now)
    async with session_factory() as session:
        assert (
            await session.get(NotificationOutbox, revoked_id)
        ).status == NotificationStatus.CANCELLED
    print(
        "outbox parallel claim, interrupted delivery, 429 delay, "
        "stale ack, revoked consent: PASS"
    )

    async with session_factory() as session, session.begin():
        await session.execute(update(Lottery).values(is_active=False))
        lotteries, due = [], []
        for index in range(2):
            lottery = Lottery(
                id=uuid4(),
                code=f"audit-recovery-{index}",
                name="Recovery",
                kind=LotteryKind.WEEKLY,
                ruleset_code="weekly_5_20",
                numbers_to_pick=5,
                max_number=20,
                ticket_price=100,
                schedule={},
                is_active=False,
                next_draw_number=3,
                next_ticket_number=1,
            )
            session.add(lottery)
            await session.flush()
            session.add(JackpotAccount(lottery_id=lottery.id, balance=0, base_amount=0))
            lotteries.append(lottery)
            for number in range(1, 3 if index == 0 else 2):
                draw = Draw(
                    id=uuid4(),
                    lottery_id=lottery.id,
                    public_number=number,
                    status=DrawStatus.DRAWING
                    if index == 0 and number == 1
                    else DrawStatus.SCHEDULED,
                    scheduled_at=now
                    - timedelta(hours=2)
                    + timedelta(minutes=index + number),
                    sales_close_at=now - timedelta(hours=3),
                    correlation_id=uuid4(),
                    winning_numbers=[1, 2, 3, 4, 5]
                    if index == 0 and number == 1
                    else None,
                    jackpot_opening=100 if index == 0 and number == 1 else None,
                    configuration_snapshot={
                        "ruleset_code": "weekly_5_20",
                        "base_jackpot": 0,
                    },
                )
                session.add(draw)
                due.append(draw)
    report = await DrawRecoveryService(session_factory).reconcile(now=now)
    assert report.failed_lottery_ids == (lotteries[0].id,)
    assert due[2].id in report.settled_draw_ids
    async with session_factory() as session:
        assert (await session.get(Draw, due[0].id)).status == DrawStatus.DRAWING
        assert (await session.get(Draw, due[1].id)).status == DrawStatus.SCHEDULED

    async def prepare():
        async with session_factory() as session:
            return await DrawScheduleService(session).ensure_next_draw(
                lotteries[1].id, reference=now
            )

    results = await asyncio.gather(prepare(), prepare())
    assert (
        results[0][0].id == results[1][0].id
        and sum(created for _, created in results) == 1
    )
    await rejected(
        update(Draw)
        .where(Draw.id == due[1].id)
        .values(scheduled_at=due[0].scheduled_at)
    )
    # The recent instant purchase must suppress the 24-hour reminder.
    async with session_factory() as session, session.begin():
        lottery = await session.get(Lottery, lotteries[1].id)
        lottery.is_active = True
    assert (
        user.id
        not in (
            await PlayerEngagementService(session_factory).run(now=now)
        ).invited_user_ids
    )
    print(
        "chronological recovery isolation, concurrent preparation, "
        "unique slots, instant activity: PASS"
    )

    # Exercise actual JSONB filtering/locks with synthetic snapshots.
    # The renderer and transport are fake.
    queued_id, archived_id, interrupted_id = uuid4(), uuid4(), uuid4()
    async with session_factory() as session, session.begin():
        state = await PublicationEventService(session)._state("publication.transport")
        state.value = {"enabled": True}
        for identifier, status, delivery in (
            (queued_id, "draft", {"state": "queued", "manual": True}),
            (archived_id, "archived", {"state": "uncertain"}),
            (
                interrupted_id,
                "draft",
                {
                    "state": "sending",
                    "attempted_at": (now - timedelta(minutes=6)).isoformat(),
                },
            ),
        ):
            session.add(
                Publication(
                    id=identifier,
                    author_id=user.id,
                    lottery_code="weekly",
                    status=status,
                    event_type="A1.1",
                    event_key=str(identifier),
                    revision=1,
                    content={
                        "event": {"occurred_at": now.isoformat(), "payload": {}},
                        "delivery": delivery,
                        "channel_caption": "Synthetic smoke",
                        "fields": {},
                    },
                )
            )

    class Transport:
        calls = 0

        async def send_photo(self, *args, **kwargs):
            self.calls += 1
            return SimpleNamespace(message_id=77, chat=SimpleNamespace(id=-77))

    transport = Transport()
    with (
        patch(
            "k_loto.application.publication_automation.editorial_snapshot",
            side_effect=lambda content, _: deepcopy(content),
        ),
        patch(
            "k_loto.application.publication_automation.render_post",
            return_value=b"fake-image",
        ),
    ):
        assert await deliver_one(session_factory, transport, now=now) == "uncertain"
        assert transport.calls == 0
        async with session_factory() as session:
            pending = await session.get(Publication, interrupted_id)
            assert pending.content["delivery"]["state"] == "uncertain"
        async with session_factory() as session:
            await PublicationService(session).change(
                interrupted_id, author=user.id, revision=1, action="archive"
            )
        assert await deliver_one(session_factory, transport, now=now) == "sent"
        assert transport.calls == 1
        async with session_factory() as session, session.begin():
            for offset in (1, 2):
                identifier = uuid4()
                session.add(
                    Publication(
                        id=identifier,
                        author_id=user.id,
                        lottery_code="weekly",
                        status="draft",
                        event_type="A1.1",
                        event_key=str(identifier),
                        revision=1,
                        content={
                            "event": {
                                "occurred_at": (
                                    now + timedelta(seconds=offset)
                                ).isoformat(),
                                "payload": {},
                            },
                            "delivery": {"state": "queued", "manual": True},
                            "channel_caption": "Synthetic smoke",
                            "fields": {},
                        },
                    )
                )
        with patch(
            "k_loto.application.publication_automation.render_post",
            side_effect=[ValueError("invalid artwork"), b"fake-image"],
        ):
            assert await deliver_one(session_factory, transport, now=now) == "failed"
            assert transport.calls == 1
            assert await deliver_one(session_factory, transport, now=now) == "sent"
            assert transport.calls == 2
        late_id = uuid4()
        async with session_factory() as session, session.begin():
            session.add(
                Publication(
                    id=late_id,
                    author_id=user.id,
                    lottery_code="weekly",
                    status="draft",
                    event_type="A1.1",
                    event_key=str(late_id),
                    revision=1,
                    content={
                        "event": {"occurred_at": now.isoformat(), "payload": {}},
                        "delivery": {"state": "queued"},
                        "channel_caption": "Late receipt smoke",
                        "fields": {},
                    },
                )
            )

        class LateTransport:
            async def send_photo(self, *args, **kwargs):
                # Simulate acknowledgement/DB finalization taking longer than the
                # interruption window, while the owner explicitly archives it.
                async with session_factory() as session, session.begin():
                    row = await session.get(Publication, late_id, with_for_update=True)
                    content = deepcopy(row.content)
                    content["delivery"]["attempted_at"] = (
                        now - timedelta(minutes=6)
                    ).isoformat()
                    row.content = content
                async with session_factory() as session:
                    await PublicationService(session).change(
                        late_id, author=user.id, revision=1, action="archive"
                    )
                return SimpleNamespace(message_id=88, chat=SimpleNamespace(id=-88))

        assert (
            await deliver_one(session_factory, LateTransport(), now=now) == "archived"
        )
        async with session_factory() as session:
            row = await session.get(Publication, late_id)
            assert (
                row.status == "archived"
                and row.content["delivery"]["state"] == "cancelled"
            )
            assert row.content["delivery"]["message_id"] == 88
            state = await PublicationEventService(session)._state(
                "publication.transport"
            )
            assert (
                state.value["last_automatic_sent_at"]
                == row.content["delivery"]["sent_at"]
            )
    print(
        "publication interrupted claim, audited archive, "
        "archived rows do not block queue: PASS"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
