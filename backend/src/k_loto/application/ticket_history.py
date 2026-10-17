"""Bounded, deterministic history selection; completed business rows are read-only."""

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, literal, select, tuple_, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from k_loto.application.query_scope import LotteryScope, lottery_scope
from k_loto.domain.enums import TicketStatus
from k_loto.domain.instant import INSTANT_GAMES, instant_versions
from k_loto.infrastructure.database.models import Draw, InstantTicket, Lottery, Ticket


@dataclass(frozen=True, slots=True)
class HistorySelection:
    keys: tuple[tuple[str, UUID], ...]
    draw_rows: tuple[Any, ...]
    instant_rows: tuple[InstantTicket, ...]
    next_cursor: str | None
    has_more: bool


class TicketHistoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def page(
        self,
        user_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
        cursor: str | None = None,
        lottery_code: str | None = None,
        wins_only: bool = False,
        scope: LotteryScope = "all",
    ) -> HistorySelection:
        if (
            not 1 <= limit <= 200
            or not 0 <= offset < 2**63 - limit
            or (cursor and offset)
        ):
            raise ValueError("Invalid history pagination.")
        binding = [str(user_id), lottery_code or "", wins_only, scope]
        boundary = decode_cursor(cursor, binding) if cursor else None
        only_instant = lottery_code in INSTANT_GAMES
        include_instant = (not lottery_code and scope == "all") or only_instant
        branches = []
        if not only_instant:
            conditions = [
                Ticket.user_id == user_id,
                Ticket.status.in_((TicketStatus.SETTLED, TicketStatus.REFUNDED)),
                lottery_scope(scope),
            ]
            if lottery_code:
                conditions.append(Lottery.code == lottery_code)
            if wins_only:
                conditions.append(Ticket.prize_amount > 0)
            branches.append(
                select(
                    Ticket.id.label("id"),
                    literal("DRAW").label("kind"),
                    Draw.scheduled_at.label("at"),
                    Ticket.public_number.label("number"),
                    literal(1).label("rank"),
                )
                .join(Draw, Draw.id == Ticket.draw_id)
                .join(Lottery, Lottery.id == Ticket.lottery_id)
                .where(*conditions)
            )
        if include_instant:
            instant_conditions = [InstantTicket.user_id == user_id]
            if only_instant and lottery_code:
                instant_conditions.append(
                    InstantTicket.odds_version.in_(instant_versions(lottery_code))
                )
            if wins_only:
                instant_conditions.append(InstantTicket.prize_amount > 0)
            branches.append(
                select(
                    InstantTicket.id.label("id"),
                    literal("INSTANT").label("kind"),
                    InstantTicket.purchased_at.label("at"),
                    InstantTicket.public_number.label("number"),
                    literal(0).label("rank"),
                ).where(*instant_conditions)
            )
        # Seek separately in each source. Only a page of identifiers crosses the
        # merge boundary; no growing prefix of ticket payloads is materialized.
        bounded = []
        for branch in branches:
            source = branch.subquery()
            statement = select(source)
            key = tuple_(source.c.at, source.c.number, source.c.rank, source.c.id)
            if boundary:
                statement = statement.where(
                    key < tuple_(*(literal(value) for value in boundary))
                )
            statement = statement.order_by(
                source.c.at.desc(),
                source.c.number.desc(),
                source.c.rank.desc(),
                source.c.id.desc(),
            ).limit(limit + offset + 1)
            bounded.append(select(statement.subquery()))
        merged = union_all(*bounded).subquery()
        selected = list(
            (
                await self.session.execute(
                    select(merged)
                    .order_by(
                        merged.c.at.desc(),
                        merged.c.number.desc(),
                        merged.c.rank.desc(),
                        merged.c.id.desc(),
                    )
                    .offset(offset)
                    .limit(limit + 1)
                )
            ).all()
        )
        has_more = len(selected) > limit
        selected = selected[:limit]
        draw_ids = [row.id for row in selected if row.kind == "DRAW"]
        instant_ids = [row.id for row in selected if row.kind == "INSTANT"]
        draw_rows: tuple[Any, ...] = ()
        if draw_ids:
            selected_draws = select(Ticket.draw_id).where(
                Ticket.id.in_(draw_ids), Ticket.user_id == user_id
            )
            group_conditions = [
                Ticket.user_id == user_id,
                Ticket.draw_id.in_(selected_draws),
                Ticket.status.in_((TicketStatus.SETTLED, TicketStatus.REFUNDED)),
            ]
            if wins_only:
                group_conditions.append(Ticket.prize_amount > 0)
            groups = (
                select(Ticket.draw_id, func.count(Ticket.id).label("count"))
                .where(*group_conditions)
                .group_by(Ticket.draw_id)
                .subquery()
            )
            second = aliased(Draw)
            draw_rows = tuple(
                (
                    await self.session.execute(
                        select(
                            Ticket,
                            Draw,
                            second,
                            Lottery,
                            groups.c.count,
                        )
                        .join(Draw, Draw.id == Ticket.draw_id)
                        .outerjoin(second, second.id == Ticket.second_draw_id)
                        .join(Lottery, Lottery.id == Ticket.lottery_id)
                        .join(groups, groups.c.draw_id == Ticket.draw_id)
                        .where(Ticket.id.in_(draw_ids), Ticket.user_id == user_id)
                    )
                ).all()
            )
        instant_rows: tuple[InstantTicket, ...] = ()
        if instant_ids:
            instant_rows = tuple(
                (
                    await self.session.scalars(
                        select(InstantTicket).where(
                            InstantTicket.id.in_(instant_ids),
                            InstantTicket.user_id == user_id,
                        )
                    )
                ).all()
            )
        last = selected[-1] if selected else None
        next_cursor = (
            encode_cursor(binding, (last.at, last.number, last.rank, last.id))
            if has_more and last
            else None
        )
        return HistorySelection(
            tuple((row.kind, row.id) for row in selected),
            draw_rows,
            instant_rows,
            next_cursor,
            has_more,
        )


def encode_cursor(binding: list[Any], key: tuple[datetime, int, int, UUID]) -> str:
    payload = [
        1,
        binding,
        [key[0].astimezone(UTC).isoformat(), key[1], key[2], str(key[3])],
    ]
    return (
        base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )


def decode_cursor(value: str, binding: list[Any]) -> tuple[datetime, int, int, UUID]:
    try:
        if len(value) > 1024:
            raise ValueError
        version, owner_filter, key = json.loads(
            base64.b64decode(
                value + "=" * (-len(value) % 4), altchars=b"-_", validate=True
            )
        )
        if version != 1 or owner_filter != binding or len(key) != 4:
            raise ValueError
        at = datetime.fromisoformat(key[0])
        if (
            at.utcoffset() is None
            or type(key[1]) is not int
            or not 1 <= key[1] < 2**63
            or type(key[2]) is not int
            or key[2] not in (0, 1)
            or not isinstance(key[3], str)
        ):
            raise ValueError
        return at.astimezone(UTC), key[1], key[2], UUID(key[3])
    except (
        ValueError,
        TypeError,
        KeyError,
        binascii.Error,
        OverflowError,
        RecursionError,
    ) as error:
        raise ValueError(
            "History cursor is invalid for this player or filter."
        ) from error
