"""Explicit one-time management replay of new projections, never an API read."""

from uuid import UUID

from sqlalchemy import and_, delete, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.achievement_progress import ExtendedProgress
from k_loto.application.achievement_results import instant_result, ticket_result
from k_loto.infrastructure.database.achievement_models import (
    AchievementEvent,
    AchievementPlayer,
    AchievementRuntime,
    AchievementWinningDraw,
)
from k_loto.infrastructure.database.models import Draw, InstantTicket, Lottery, Ticket


async def initialize_extended_progress(
    session: AsyncSession, runtime: AchievementRuntime, *, revision: int = 1
) -> None:
    if runtime.projection_revision >= revision:
        return
    if runtime.started_at is None:
        runtime.projection_revision = revision
        return
    wins_only = runtime.projection_revision >= 1
    if wins_only:
        # Derived projections only. The immutable source tickets/awards stay intact.
        await session.execute(delete(AchievementWinningDraw))
        await session.execute(
            text(
                "UPDATE achievement_players SET metrics=metrics-ARRAY["
                "'consecutive_winning_draws','max_draw_winning_tickets',"
                "'daily_fast_winning_games']"
            )
        )
    last = 0
    while True:
        events = list(
            (
                await session.scalars(
                    select(AchievementEvent)
                    .where(
                        AchievementEvent.id > last,
                        AchievementEvent.kind.in_(
                            ["purchase", "refund", "instant", "draw"]
                        ),
                    )
                    .order_by(AchievementEvent.id)
                    .limit(100)
                )
            ).all()
        )
        if not events:
            break
        progress = ExtendedProgress(session)
        for event in events:
            last = event.id
            if event.kind == "draw":
                if not event.cursor:
                    continue
                draw = await session.get(Draw, UUID(event.payload["draw"]))
                assert draw is not None
                lottery = await session.get(Lottery, draw.lottery_id)
                assert lottery is not None
                cursor = None
                while True:
                    query = select(Ticket).where(
                        Ticket.status == "SETTLED",
                        Ticket.purchase_price > 0,
                        Ticket.purchased_at >= runtime.started_at,
                        Ticket.id <= UUID(event.cursor),
                        or_(
                            and_(
                                Ticket.draw_id == draw.id,
                                Ticket.second_draw_id.is_(None),
                            ),
                            Ticket.second_draw_id == draw.id,
                        ),
                    )
                    if cursor:
                        query = query.where(Ticket.id > cursor)
                    tickets = list(
                        (
                            await session.scalars(query.order_by(Ticket.id).limit(100))
                        ).all()
                    )
                    if not tickets:
                        break
                    for ticket in tickets:
                        player = await session.get(AchievementPlayer, ticket.user_id)
                        assert player is not None
                        metrics = dict(player.metrics)
                        await progress.win(
                            player.user_id,
                            ticket_result(ticket, draw, lottery),
                            draw.scheduled_at,
                            metrics,
                            draw=draw,
                        )
                        player.metrics = metrics
                    await session.flush()
                    progress.days.clear()
                    progress.winning_draws.clear()
                    progress.draw_records.clear()
                    cursor = tickets[-1].id
            elif event.processed_at:
                player = await session.get(AchievementPlayer, event.user_id)
                assert player is not None
                metrics = dict(player.metrics)
                if event.kind == "instant":
                    instant = await session.get(
                        InstantTicket, UUID(event.payload["ticket"])
                    )
                    assert instant is not None
                    if wins_only:
                        await progress.win(
                            instant.user_id,
                            instant_result(instant),
                            instant.purchased_at,
                            metrics,
                        )
                    else:
                        await progress.instant(
                            instant, instant_result(instant), metrics
                        )
                elif not wins_only:
                    lottery = await session.get(Lottery, UUID(event.payload["lottery"]))
                    assert lottery is not None
                    await progress.purchase(event, lottery.code, metrics)
                player.metrics = metrics
            await session.flush()
            progress.days.clear()
            progress.neighbours.clear()
    # Existing global/scoped winning counts already include only eligible tickets.
    cursor_user = None
    while True:
        player_query = (
            select(AchievementPlayer).order_by(AchievementPlayer.user_id).limit(100)
        )
        if cursor_user:
            player_query = player_query.where(AchievementPlayer.user_id > cursor_user)
        players = list((await session.scalars(player_query)).all())
        if not players:
            break
        for existing_player in players:
            existing_player.metrics = {
                **existing_player.metrics,
                "winning_lotteries": sum(
                    key.startswith("winning_tickets:") and value > 0
                    for key, value in existing_player.metrics.items()
                ),
            }
        await session.flush()
        cursor_user = players[-1].user_id
    runtime.projection_revision = revision
