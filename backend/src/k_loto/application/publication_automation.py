"""A/B collection, approved snapshots and durable single-message delivery.

The outbox is stored in the existing Publication JSONB snapshot. An in-flight send
is committed BEFORE Telegram I/O. A lost response never causes an automatic retry.
Financial history is read-only. Historical authorization has an explicit cutoff.
"""

import asyncio
import hashlib
import html
import json
import random
import re
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from importlib.resources import files
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import BufferedInputFile
from sqlalchemy import and_, distinct, func, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from k_loto.application.publication_events import (
    LOTTERY_EVENTS,
    EventDefinition,
    PublicationEventService,
    day_bounds,
    event_config,
)
from k_loto.application.publication_render import render_post
from k_loto.application.publications import template_catalog
from k_loto.core.config import get_settings
from k_loto.domain.enums import DrawStatus, LedgerAccountKind, TransactionType
from k_loto.infrastructure.database.models import (
    Draw,
    InstantTicket,
    JackpotAccount,
    JackpotWinEvent,
    LedgerTransaction,
    Lottery,
    Publication,
    Ticket,
    User,
)

MOSCOW = ZoneInfo("Europe/Moscow")
MINIAPP_URL = "https://t.me/Kasper_loto_bot/app"
MINIAPP_LINK_LABEL = "Открыть Casper Loto →"
AUTOMATIC_A = {"A1.1", "A1.2", "A1.3", "A1.4", "A1.5", "A4.1", "A4.2", "A5.5"}
for _code in AUTOMATIC_A | {
    "A2.1",
    "A2.2",
    "A2.3",
    "A3.1",
    "A3.2",
    "A3.4",
    "A5.1",
    "A5.3",
    "A5.5",
    "A5.6",
}:
    LOTTERY_EVENTS[_code] = EventDefinition(
        _code,
        next(
            t["subcategoryLabel"]
            for t in template_catalog()
            if t["subcategory"] == _code
        ),
        "automatic" if _code in AUTOMATIC_A else "draft",
        "lottery",
    )


def number(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def lottery_publication_rules() -> dict[str, Any]:
    rules: dict[str, Any] = json.loads(
        files("k_loto.application")
        .joinpath("publication_lottery_config.json")
        .read_text(encoding="utf-8")
    )
    return rules


def unique_winners_record_eligible(current: int, previous: int) -> bool:
    return (
        current > lottery_publication_rules()["unique_winners_record_exclusive_minimum"]
        and current > previous
    )


def jackpot_record_eligible(current: int, previous: int) -> bool:
    return current - previous >= int(
        lottery_publication_rules()["jackpot_record_minimum_increase_cas"]
    )


def publication_is_eligible(
    code: str | None, game: str, payload: dict[str, Any] | None = None
) -> bool:
    """Historical approval changes delivery mode, never event eligibility."""
    rules = lottery_publication_rules()
    if code in {"A1.3", "A1.4", "B2.1"}:
        if not payload or not jackpot_record_eligible(
            int(payload.get("new_record", 0)),
            int(payload.get("publication_baseline", payload.get("previous_record", 0))),
        ):
            return False
    if code == "A5.5":
        if not payload or payload.get("metric") != "unique_winners_per_draw":
            return False
        if not unique_winners_record_eligible(
            payload["new_record"], payload["previous_record"]
        ):
            return False
    return (
        game not in rules["excluded_games"]
        and (code is None or code in rules["enabled_channel_events"])
        and code not in rules["unresolved_events"]
        and not (
            game in rules["fast_games"]
            and code in rules["fast_excluded_routine_events"]
        )
    )


def publication_eligibility_filter() -> Any:
    """Same eligibility at the persisted outbox boundary, including old rows."""
    rules = lottery_publication_rules()
    payload = Publication.content["event"]["payload"]
    predicate = and_(
        Publication.lottery_code.not_in(rules["excluded_games"]),
        func.coalesce(
            Publication.event_type,
            Publication.content["template"]["subcategory"].astext,
            "",
        ).not_in(rules["retired_event_types"]),
        or_(
            Publication.event_type.is_(None),
            and_(
                Publication.event_type.in_(rules["enabled_channel_events"]),
                Publication.event_type.not_in(rules["unresolved_events"]),
                or_(
                    Publication.event_type.not_in(["A1.3", "A1.4", "B2.1"]),
                    payload["new_record"].as_integer()
                    - func.coalesce(
                        payload["publication_baseline"].as_integer(),
                        payload["previous_record"].as_integer(),
                    )
                    >= rules["jackpot_record_minimum_increase_cas"],
                ),
                or_(
                    Publication.event_type != "A5.5",
                    and_(
                        payload["metric"].astext == "unique_winners_per_draw",
                        payload["new_record"].as_integer()
                        > rules["unique_winners_record_exclusive_minimum"],
                        payload["new_record"].as_integer()
                        > payload["previous_record"].as_integer(),
                    ),
                ),
                ~and_(
                    Publication.lottery_code.in_(rules["fast_games"]),
                    Publication.event_type.in_(rules["fast_excluded_routine_events"]),
                ),
            ),
        ),
    )
    # Missing legacy payload fields are ineligible, including under NOT(predicate).
    return func.coalesce(predicate, False)


def moscow(value: datetime) -> str:
    return value.astimezone(MOSCOW).strftime("%d.%m.%Y %H:%M МСК")


def format_key(snapshot: dict[str, Any]) -> str:
    fields = {
        k: v for k, v in snapshot.items() if k not in {"base_jackpot", "ticket_price"}
    }
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()[:16]


def caption_html(text: str) -> str:
    visible = re.sub(r"\[ПОД СПОЙЛЕРОМ: (.*?)\]", r"\1", text)
    has_link = "t.me/Kasper_loto_bot/app" in text
    visible += "" if has_link else "\n\n" + MINIAPP_LINK_LABEL
    if len(visible.encode("utf-16-le")) // 2 > 1024:
        raise ValueError("Caption with Mini App link exceeds Telegram photo limit")
    escaped = html.escape(text)
    caption = re.sub(
        r"\[ПОД СПОЙЛЕРОМ: (.*?)\]", r"<tg-spoiler>\1</tg-spoiler>", escaped
    )
    if not has_link:
        caption += f'\n\n<a href="{MINIAPP_URL}">{MINIAPP_LINK_LABEL}</a>'
    return caption


def editorial_snapshot(content: dict[str, Any], game: str) -> dict[str, Any]:
    """Apply current presentation rules even to previously prepared queue rows."""
    result = deepcopy(content)
    result["channel_caption"] = re.sub(
        r"\n\nСобытие: [^\n]*\Z", "", result.get("channel_caption", "")
    )
    code = result.get("event", {}).get("type", "")
    if not (code.startswith("A1.") or code in {"B2.1", "B3.1", "B3.5"}):
        result.get("fields", {}).update(fact="")
    template = result.get("template", {})
    if game in lottery_publication_rules()["fast_games"] and not template.get(
        "id", ""
    ).startswith("fast-owner-v1-"):
        approved = [
            t
            for t in template_catalog()
            if t["lottery"] == game
            and t["subcategory"] == template.get("subcategory")
            and t["id"].startswith("fast-owner-v1-")
        ]
        if not approved:
            raise ValueError("No owner Fast template for queued publication")
        result["template"] = deepcopy(approved[0])
    return result


def choose(
    options: list[Any], previous: list[str], key: str, *, identifier: str = "id"
) -> Any:
    available = [item for item in options if item[identifier] not in previous]
    if not available:
        return min(
            options,
            key=lambda item: (
                previous.index(item[identifier]) if item[identifier] in previous else -1
            ),
        )
    return random.Random(key).choice(available)


class PublicationAutomation:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.events = PublicationEventService(session)
        self.library = json.loads(
            files("k_loto.application")
            .joinpath("publication_copy.json")
            .read_text(encoding="utf-8")
        )
        self.rules = lottery_publication_rules()

    async def snapshot(
        self, row: Publication, values: dict[str, str], *, historical: bool
    ) -> None:
        if not publication_is_eligible(
            row.event_type,
            row.lottery_code,
            row.content.get("event", {}).get("payload"),
        ):
            return
        if "template" in row.content or row.status != "draft":
            return
        code = row.event_type
        assert code is not None and row.event_key is not None
        templates = [
            t
            for t in template_catalog()
            if t["lottery"] == row.lottery_code and t["subcategory"] == code
        ]
        if not templates:
            raise ValueError(f"No approved template for {row.lottery_code}/{code}")
        rotation = await self.events._state(f"rotation:{row.lottery_code}:{code}")
        # Different compositions of one background still count as the same image.
        backgrounds: dict[str, dict[str, Any]] = {}
        for template in templates:
            backgrounds.setdefault(
                template["formats"]["post"]["background"],
                {"id": template["formats"]["post"]["background"], "template": template},
            )
        selected = choose(
            list(backgrounds.values()),
            rotation.value.get("images", [])[-3:],
            row.event_key,
        )
        template = selected["template"]
        variants = self.library.get(code, [])
        if variants:
            variant = choose(
                variants, rotation.value.get("texts", [])[-2:], row.event_key
            )
            caption = variant["text"].format_map(values)
            # Owner's source uses a ticket counter here; do not label it as people.
            caption = caption.replace(
                "Победителей в тираже", "Выигрышных билетов в тираже"
            )
            text_id = variant["id"]
        else:
            caption = values["caption"]
            text_id = code
        title = caption.split("\n", 1)[0]
        if len(title) > 120:
            title = template["subcategoryLabel"]
        # Reserve the visible link text while preparing the snapshot too.
        caption_html(caption)
        fields = {
            "kicker": values.get("game_name", "Casper Loto"),
            "title": title,
            "value": values.get("value", ""),
            "description": values.get("description", template["subcategoryLabel"]),
            "fact": "",
        }
        if any(
            len(fields[k]) > limit
            for k, limit in {
                "kicker": 50,
                "title": 120,
                "value": 80,
                "description": 240,
                "fact": 100,
            }.items()
        ):
            raise ValueError(f"Artwork text exceeds field limit for {row.event_key}")
        snapshot = deepcopy(row.content)
        snapshot.update(
            template=deepcopy(template),
            fields=fields,
            cta_label="Открыть Casper Loto"
            if code.startswith("B")
            else "Открыть лотерею",
            channel_caption=caption,
            text_variant=text_id,
        )
        snapshot["delivery"].update(
            state="queued"
            if historical or row.event_mode == "automatic"
            else "approval_required",
            historical=historical,
        )
        row.content = snapshot
        rotation.value = {
            "images": (rotation.value.get("images", []) + [selected["id"]])[-3:],
            "texts": (rotation.value.get("texts", []) + [text_id])[-2:],
        }

    async def store(
        self,
        code: str,
        key: str,
        occurred: datetime,
        author: Any,
        values: dict[str, str],
        *,
        game: str = "casper-loto",
        payload: dict[str, Any] | None = None,
        historical: bool = False,
    ) -> Publication | None:
        if not publication_is_eligible(code, game, payload):
            return None
        row = await self.events._store(key, code, payload or {}, occurred, author, key)
        if row.status == "draft" and "template" not in row.content:
            row.lottery_code = game
            # A bootstrap scan could have observed a milestone after its real crossing.
            content = deepcopy(row.content)
            content["event"]["occurred_at"] = occurred.isoformat()
            row.content = content
        await self.snapshot(row, values, historical=historical)
        return row

    async def collect(
        self, start: datetime, end: datetime, *, historical: bool
    ) -> dict[str, int]:
        """Replay facts chronologically with pre-window baselines and stable keys."""
        async with self.session.begin():
            await self.events._lock()
            await self.events.prime_cache()
            author = await self.session.scalar(
                select(User.id)
                .where(User.is_admin.is_(True))
                .order_by(User.created_at)
                .limit(1)
            )
            if author is None:
                raise ValueError("Existing admin author required")
            games = {g.id: g for g in await self.session.scalars(select(Lottery))}
            names = {
                g.code: next(
                    (
                        t["lotteryLabel"]
                        for t in template_catalog()
                        if t["lottery"] == g.code
                    ),
                    g.name,
                )
                for g in games.values()
            }
            excluded = set(self.rules["excluded_games"])
            wins = list(
                await self.session.scalars(
                    select(JackpotWinEvent)
                    .where(JackpotWinEvent.occurred_at <= end)
                    .order_by(JackpotWinEvent.occurred_at, JackpotWinEvent.id)
                )
            )
            win_draws = {w.draw_id: w for w in wins}
            for win in wins:
                if start <= win.occurred_at < end:
                    game = games[win.lottery_id].code
                    if game not in excluded:
                        await self.store(
                            "A1.1",
                            f"A1.1:draw:{win.draw_id}",
                            win.occurred_at,
                            author,
                            dict(
                                game_name=names[game],
                                draw_number=number(
                                    int(
                                        await self.session.scalar(
                                            select(Draw.public_number).where(
                                                Draw.id == win.draw_id
                                            )
                                        )
                                        or 0
                                    )
                                ),
                                jackpot_cas=number(win.jackpot_amount),
                                winning_tickets_count=number(win.winner_ticket_count),
                                value=f"{number(win.jackpot_amount)} CAS",
                                description=(
                                    "Выигрышных билетов: "
                                    + number(win.winner_ticket_count)
                                ),
                                game_hashtag="#" + re.sub(r"\W", "", names[game]),
                                topic_hashtag="#Джекпот",
                                public_topic_hashtag="#джекпот",
                            ),
                            game=game,
                            payload={"win_event_id": str(win.id)},
                            historical=historical,
                        )
            payouts = {
                key: int(count)
                for key, count in (
                    await self.session.execute(
                        select(
                            LedgerTransaction.draw_id,
                            func.count(distinct(LedgerTransaction.ticket_id)),
                        )
                        .where(
                            LedgerTransaction.type.in_(
                                [
                                    TransactionType.PRIZE_PAYOUT,
                                    TransactionType.JACKPOT_PAYOUT,
                                ]
                            ),
                            LedgerTransaction.amount > 0,
                        )
                        .group_by(LedgerTransaction.draw_id)
                    )
                ).all()
            }
            draws = list(
                await self.session.scalars(
                    select(Draw)
                    .where(Draw.status == DrawStatus.COMPLETED, Draw.executed_at < end)
                    .order_by(Draw.scheduled_at, Draw.public_number, Draw.id)
                )
            )
            attachments = union_all(
                select(Ticket.draw_id.label("draw"), Ticket.user_id.label("user")),
                select(
                    Ticket.second_draw_id.label("draw"), Ticket.user_id.label("user")
                ).where(Ticket.second_draw_id.is_not(None)),
            ).subquery()
            participant_counts = {
                key: int(count)
                for key, count in (
                    await self.session.execute(
                        select(
                            attachments.c.draw, func.count(distinct(attachments.c.user))
                        ).group_by(attachments.c.draw)
                    )
                ).all()
            }
            paid_tickets = (
                select(
                    LedgerTransaction.draw_id.label("draw"),
                    LedgerTransaction.ticket_id.label("ticket"),
                    func.sum(LedgerTransaction.amount).label("prize"),
                    func.max(LedgerTransaction.created_at).label("at"),
                )
                .where(
                    LedgerTransaction.type.in_(
                        [TransactionType.PRIZE_PAYOUT, TransactionType.JACKPOT_PAYOUT]
                    ),
                    LedgerTransaction.amount > 0,
                    LedgerTransaction.ticket_id.is_not(None),
                )
                .group_by(LedgerTransaction.draw_id, LedgerTransaction.ticket_id)
                .subquery()
            )
            largest_prizes = {
                key: int(prize)
                for key, prize in (
                    await self.session.execute(
                        select(
                            paid_tickets.c.draw, func.max(paid_tickets.c.prize)
                        ).group_by(paid_tickets.c.draw)
                    )
                ).all()
            }
            winner_users = {
                key: int(count)
                for key, count in (
                    await self.session.execute(
                        select(
                            LedgerTransaction.draw_id,
                            func.count(distinct(LedgerTransaction.user_id)),
                        )
                        .where(
                            LedgerTransaction.type.in_(
                                [
                                    TransactionType.PRIZE_PAYOUT,
                                    TransactionType.JACKPOT_PAYOUT,
                                ]
                            ),
                            LedgerTransaction.amount > 0,
                        )
                        .group_by(LedgerTransaction.draw_id)
                    )
                ).all()
            }
            prize_records: dict[str, int] = {}
            streaks: dict[str, int] = {}
            epochs: dict[str, str] = {}
            ticket_records: dict[str, int] = {}
            player_records: dict[str, int] = {}
            winner_records: dict[str, int] = {}
            for draw in draws:
                game = games[draw.lottery_id].code
                if game in excluded:
                    continue
                assert draw.executed_at is not None
                from k_loto.application.jackpot_cycles import cycle_ended

                streaks[game] = (
                    0 if cycle_ended(draw, win_draws) else streaks.get(game, 0) + 1
                )
                if cycle_ended(draw, win_draws):
                    epochs[game] = str(draw.id)
                record_key = game + ":" + format_key(draw.configuration_snapshot)
                old_tickets = ticket_records.get(record_key, 0)
                ticket_records[record_key] = max(old_tickets, draw.ticket_count)
                # Include both phases of purchased Dual tickets, once per draw.
                participants = int(participant_counts.get(draw.id, 0))
                old_players = player_records.get(record_key, 0)
                player_records[record_key] = max(old_players, participants)
                unique_winners = int(winner_users.get(draw.id, 0))
                previous_winners = winner_records.get(record_key, 0)
                winner_records[record_key] = max(previous_winners, unique_winners)
                prize = largest_prizes.get(draw.id, 0)
                previous_prize = prize_records.get(record_key, 0)
                prize_records[record_key] = max(previous_prize, prize)
                if not start <= draw.executed_at < end:
                    continue
                if unique_winners_record_eligible(unique_winners, previous_winners):
                    await self.store(
                        "A5.5",
                        f"A5.5:unique-winners:draw:{draw.id}",
                        draw.executed_at,
                        author,
                        dict(
                            game_name=names[game],
                            value=number(unique_winners),
                            description="Уникальных победителей за один тираж",
                            caption=(
                                f"Рекорд уникальных победителей · {names[game]}\n\n"
                                f"В тираже №{draw.public_number} выиграли "
                                f"{number(unique_winners)} человек. "
                                "Предыдущий рекорд в действующем формате: "
                                f"{number(previous_winners)}.\n\n"
                                f"#{re.sub(r'\W', '', names[game])} #Рекорд"
                            ),
                        ),
                        game=game,
                        payload={
                            "metric": "unique_winners_per_draw",
                            "new_record": unique_winners,
                            "previous_record": previous_winners,
                            "draw_id": str(draw.id),
                            "format": record_key,
                        },
                        historical=historical,
                    )
                values = dict(
                    game_name=names[game],
                    draw_number=number(draw.public_number),
                    winning_tickets_count=number(payouts.get(draw.id, 0)),
                    tickets_count=number(draw.ticket_count),
                    players_count=number(participants),
                    previous_record_players=number(old_players),
                    game_hashtag="#" + re.sub(r"\W", "", names[game]),
                    topic_hashtag="#Результаты",
                    public_topic_hashtag="#лотерея",
                    comparison_scope_label="в действующем формате",
                    counter_scope_label="за один тираж",
                    draws_without_jackpot=number(streaks[game]),
                    jackpot_cas=number(draw.jackpot_closing or 0),
                )
                result = (
                    f"Тираж №{draw.public_number} завершён · {names[game]}\n\n"
                    f"Куплено билетов: {number(draw.ticket_count)}. "
                    f"Выигрышных билетов: {number(payouts.get(draw.id, 0))}. "
                    f"Выплачено: {number(draw.total_payout)} CAS.\n\n"
                    f"{values['game_hashtag']} #Результаты"
                )
                if draw.ticket_count:
                    await self.store(
                        "A2.1",
                        f"A2.1:draw:{draw.id}",
                        draw.executed_at,
                        author,
                        {
                            **values,
                            "caption": result,
                            "value": f"{number(draw.total_payout)} CAS",
                            "description": (
                                f"Билетов: {number(draw.ticket_count)} · "
                                f"выигрышных: {number(payouts.get(draw.id, 0))}"
                            ),
                        },
                        game=game,
                        historical=historical,
                    )
                    if payouts.get(draw.id, 0) and draw.id not in win_draws:
                        users = winner_users.get(draw.id, 0)
                        code = "A3.2" if users > 1 else "A3.1"
                        await self.store(
                            code,
                            f"{code}:draw:{draw.id}",
                            draw.executed_at,
                            author,
                            {
                                **values,
                                "caption": (
                                    f"Есть выигрыши · {names[game]}\n\n"
                                    f"В тираже №{draw.public_number} "
                                    f"выигрышных билетов: {number(payouts[draw.id])}. "
                                    f"Уникальных победителей: {number(users)}.\n\n"
                                    f"{values['game_hashtag']} #Выигрыши"
                                ),
                                "value": number(payouts[draw.id]),
                                "description": "Выигрышных билетов",
                            },
                            game=game,
                            payload={
                                "winning_tickets": payouts[draw.id],
                                "winner_users": users,
                            },
                            historical=historical,
                        )
                    if prize > previous_prize:
                        await self.store(
                            "A3.4",
                            f"A3.4:draw:{draw.id}",
                            draw.executed_at,
                            author,
                            {
                                **values,
                                "caption": (
                                    f"Рекордный выигрыш · {names[game]}\n\n"
                                    f"В тираже №{draw.public_number} на один билет "
                                    f"выплачено {number(prize)} CAS. "
                                    "Предыдущий максимум в этом формате: "
                                    f"{number(previous_prize)} CAS.\n\n"
                                    f"{values['game_hashtag']} #Рекорд"
                                ),
                                "value": f"{number(prize)} CAS",
                            },
                            game=game,
                            payload={
                                "new_record": prize,
                                "previous_record": previous_prize,
                                "format": record_key,
                            },
                            historical=historical,
                        )
                    if draw.winning_numbers:
                        combination = " · ".join(str(n) for n in draw.winning_numbers)
                        await self.store(
                            "A2.2",
                            f"A2.2:draw:{draw.id}",
                            draw.executed_at,
                            author,
                            {
                                **values,
                                "caption": (
                                    f"Выигрышная комбинация · {names[game]}\n\n"
                                    f"Тираж №{draw.public_number}: {combination}.\n\n"
                                    f"{values['game_hashtag']} #Результаты"
                                ),
                                "value": combination
                                if len(combination) <= 80
                                else f"{len(draw.winning_numbers)} чисел",
                            },
                            game=game,
                            historical=historical,
                        )
                    if draw.id not in win_draws and draw.jackpot_closing:
                        await self.store(
                            "A2.3",
                            f"A2.3:draw:{draw.id}",
                            draw.executed_at,
                            author,
                            {
                                **values,
                                "caption": (
                                    f"Джекпот переходит дальше · {names[game]}\n\n"
                                    f"В тираже №{draw.public_number} "
                                    "джекпот не сорван. "
                                    "На момент завершения: "
                                    f"{number(draw.jackpot_closing)} CAS.\n\n"
                                    f"{values['game_hashtag']} #Джекпот"
                                ),
                                "value": f"{number(draw.jackpot_closing)} CAS",
                            },
                            game=game,
                            historical=historical,
                        )
                step = (
                    self.rules["fast_streak_step"]
                    if game in self.rules["fast_games"]
                    else self.rules["ordinary_streak_step"]
                )
                if streaks[game] and streaks[game] % step == 0:
                    await self.store(
                        "A1.5",
                        f"A1.5:{game}:{epochs.get(game, 'origin')}:{streaks[game]}",
                        draw.executed_at,
                        author,
                        {
                            **values,
                            "value": number(streaks[game]),
                            "topic_hashtag": "#Джекпот",
                        },
                        game=game,
                        payload={"reset_draw_id": epochs.get(game, "origin")},
                        historical=historical,
                    )
                for threshold in self.rules["ticket_milestones"]:
                    if draw.ticket_count >= threshold:
                        await self.store(
                            "A4.1",
                            f"A4.1:{draw.id}:{threshold}",
                            draw.executed_at,
                            author,
                            {
                                **values,
                                "milestone_tickets": number(threshold),
                                "value": number(threshold),
                                "topic_hashtag": "#Билеты",
                            },
                            game=game,
                            historical=historical,
                        )
                if (
                    draw.ticket_count >= self.rules["ticket_milestones"][0]
                    and draw.ticket_count > old_tickets
                ):
                    await self.store(
                        "A4.2",
                        f"A4.2:{draw.id}",
                        draw.executed_at,
                        author,
                        {
                            **values,
                            "previous_record_tickets": number(old_tickets),
                            "value": number(draw.ticket_count),
                            "topic_hashtag": "#Рекорд",
                        },
                        game=game,
                        historical=historical,
                    )
            await self._jackpot_records(
                start, end, author, games, names, wins, historical
            )
            await self._milestones(start, end, author, historical)
            if historical:
                await self._historical_statistics(start, end, author, names)
            await self.events._daily_jackpots(end, author)
            for row in await self.session.scalars(
                select(Publication).where(
                    Publication.event_type == "B3.5", Publication.status == "draft"
                )
            ):
                payload = row.content["event"]["payload"]
                day_start, day_end = day_bounds(
                    datetime.fromisoformat(payload["day"]).date()
                )
                # Historical owner override can publish the current partial day once.
                if (start <= day_start < end and historical) or (
                    not historical and start < day_end <= end
                ):
                    if "template" not in row.content:
                        content = deepcopy(row.content)
                        content["event"]["occurred_at"] = min(day_end, end).isoformat()
                        row.content = content
                    details = "\n".join(
                        f"• {names[w['lottery_code']]}: {number(w['amount'])} CAS · "
                        f"{moscow(datetime.fromisoformat(w['occurred_at']))}"
                        for w in payload["jackpots"]
                    )
                    await self.snapshot(
                        row,
                        dict(
                            jackpots_count=number(payload["count"]),
                            jackpots_list=details,
                            day_moscow=payload["day"],
                            topic_hashtag="#CasperДжекпоты",
                            public_topic_hashtag="#джекпот",
                            value=number(payload["count"]),
                        ),
                        historical=historical,
                    )
            state = await self.events._state("publication.automation")
            state.value = {**state.value, "collected_until": end.isoformat()}
            await self.session.flush()
            return {
                str(code): int(count)
                for code, count in (
                    await self.session.execute(
                        select(Publication.event_type, func.count())
                        .where(
                            Publication.content["delivery"]["state"].astext == "queued"
                        )
                        .group_by(Publication.event_type)
                    )
                ).all()
            }

    async def _statistics_a(
        self,
        start: datetime,
        end: datetime,
        author: Any,
        games: dict[Any, Any],
        names: dict[str, str],
        draws: list[Any],
        participants: dict[Any, int],
        winners: dict[Any, int],
        wins: dict[Any, Any],
        historical: bool,
    ) -> None:
        day = start.astimezone(MOSCOW).replace(
            hour=12, minute=22, second=0, microsecond=0
        )
        while day.astimezone(UTC) < end:
            slot = day.astimezone(UTC)
            if day.weekday() in (0, 2, 4) and slot >= start:
                for lottery in games.values():
                    game = lottery.code
                    if game in self.rules["excluded_games"]:
                        continue
                    history = [
                        d
                        for d in draws
                        if d.lottery_id == lottery.id and d.executed_at < slot
                    ]
                    if not history:
                        continue
                    current = format_key(history[-1].configuration_snapshot)
                    same_format = [
                        d
                        for d in history
                        if format_key(d.configuration_snapshot) == current
                    ]
                    streak = 0
                    for draw in reversed(history):
                        from k_loto.application.jackpot_cycles import cycle_ended

                        if cycle_ended(draw, wins):
                            break
                        streak += 1
                    metrics = {
                        "A5.1": (
                            max(
                                max(d.jackpot_opening or 0, d.jackpot_closing or 0)
                                for d in same_format
                            ),
                            "Максимальный джекпот завершённых тиражей",
                            "CAS",
                        ),
                        "A5.2": (
                            max(participants.get(d.id, 0) for d in same_format),
                            "Рекорд уникальных участников за тираж",
                            "участников",
                        ),
                        "A5.3": (
                            max(d.ticket_count for d in same_format),
                            "Рекорд купленных билетов за тираж",
                            "билетов",
                        ),
                        "A5.5": (
                            max(winners.get(d.id, 0) for d in same_format),
                            "Рекорд уникальных победителей за тираж",
                            "победителей",
                        ),
                        "A5.6": (streak, "Текущая серия без джекпота", "тиражей"),
                    }
                    for code, (value, label, unit) in metrics.items():
                        if value:
                            await self.store(
                                code,
                                f"{code}:{game}:{day.date()}",
                                slot,
                                author,
                                dict(
                                    game_name=names[game],
                                    value=f"{number(value)} {unit}",
                                    description=label,
                                    caption=(
                                        f"{label} · {names[game]}\n\n"
                                        f"На {moscow(slot)}: {number(value)} {unit}. "
                                        "Статистика действующего формата игры.\n\n"
                                        "#CasperLoto #Статистика"
                                    ),
                                ),
                                game=game,
                                payload={
                                    "value": value,
                                    "format": current,
                                    "reset_draw_id": str(history[-streak - 1].id)
                                    if streak < len(history)
                                    else "origin",
                                },
                                historical=historical,
                            )
            day += timedelta(days=1)

    async def prepare_suggestions(self, *, author: Any, now: datetime) -> None:
        """Prepare current drafts, retaining daily rejection tombstones."""
        async with self.session.begin():
            await self.events._lock()
            names = {
                item["lottery"]: item["lotteryLabel"] for item in template_catalog()
            }
            await self._historical_statistics(
                now - timedelta(days=7),
                now,
                author,
                names,
                historical=False,
                key_suffix=f"suggestion:{now.astimezone(MOSCOW).date()}",
            )

    async def _historical_statistics(
        self,
        start: datetime,
        end: datetime,
        author: Any,
        names: dict[str, str],
        *,
        historical: bool = True,
        key_suffix: str | None = None,
    ) -> None:
        """One owner-requested snapshot; never creates a recurring summary job."""
        day = end.astimezone(MOSCOW).date()
        suffix = key_suffix or f"owner-backfill:{end.isoformat()}"
        day_start, _ = day_bounds(day)
        common = dict(
            as_of_moscow=moscow(end),
            day_moscow=day.strftime("%d.%m.%Y"),
            topic_hashtag="#CasperСтатистика",
            public_topic_hashtag="#статистика",
        )
        total = int(
            await self.session.scalar(
                select(func.sum(JackpotAccount.balance))
                .join(Lottery, Lottery.id == JackpotAccount.lottery_id)
                .where(Lottery.code != "daily")
            )
            or 0
        )
        await self.store(
            "B3.1",
            f"B3.1:{suffix}",
            end,
            author,
            {
                **common,
                "total_jackpot_cas": number(total),
                "value": f"{number(total)} CAS",
            },
            payload={"total_jackpot": total, "unit": "CAS"},
            historical=historical,
        )
        winners = await self.events._winning_period(day_start, end)
        await self.store(
            "B3.2",
            f"B3.2:{suffix}",
            end,
            author,
            {
                **common,
                "winning_tickets_today": number(winners),
                "value": number(winners),
            },
            payload={"day": str(day), "count": winners},
            historical=historical,
        )
        week_start = end - timedelta(days=7)
        activity = await self.events._activity(week_start, end)
        await self.store(
            "B3.3",
            f"B3.3:{suffix}",
            end,
            author,
            {
                **common,
                "period_moscow": f"{moscow(week_start)} — {moscow(end)}",
                "period_tickets": number(activity["purchased_tickets"]),
                "period_players": number(activity["active_players"]),
                "period_winning_tickets": number(activity["winning_tickets"]),
                "period_draws": number(activity["completed_draws"]),
                "value": number(activity["purchased_tickets"]),
                "description": "Купленных билетов за выбранную неделю",
            },
            payload=activity,
            historical=historical,
        )
        popularity = await self.events._activity(start, end)
        leaders = popularity["most_popular_lotteries"]
        if leaders:
            label = ", ".join(
                names.get(code, "Моментальная лотерея") for code in leaders
            )
            leader_tickets = popularity["tickets_by_lottery"][leaders[0]]
            await self.store(
                "B3.4",
                f"B3.4:{suffix}",
                end,
                author,
                {
                    **common,
                    "period_moscow": f"{moscow(start)} — {moscow(end)}",
                    "popular_games_label": label,
                    "leader_tickets": number(leader_tickets),
                    "value": number(leader_tickets),
                    "description": label,
                },
                payload=popularity,
                historical=historical,
            )

    async def _milestones(
        self, start: datetime, end: datetime, author: Any, historical: bool
    ) -> None:
        purchased = union_all(
            select(Ticket.purchased_at.label("at")),
            select(InstantTicket.purchased_at.label("at")),
        ).subquery()
        winning = union_all(
            select(Ticket.settled_at.label("at")).where(Ticket.prize_amount > 0),
            select(InstantTicket.settled_at.label("at")).where(
                InstantTicket.prize_amount > 0
            ),
        ).subquery()
        sources = {
            "B1.1": User.created_at,
            "B1.2": purchased.c.at,
            "B1.3": Draw.executed_at,
            "B1.4": winning.c.at,
        }
        for code, rule in event_config().milestones.items():
            column = sources[code]
            query = select(column).where(column < end)
            if code == "B1.3":
                query = query.where(Draw.status == DrawStatus.COMPLETED)
            count = int(
                await self.session.scalar(
                    select(func.count()).select_from(query.subquery())
                )
                or 0
            )
            for threshold in rule.reached(count):
                at = await self.session.scalar(
                    query.order_by(column).offset(threshold - 1).limit(1)
                )
                if at is not None and start <= at < end:
                    placeholder = {
                        "B1.1": "milestone_players",
                        "B1.2": "milestone_tickets",
                        "B1.3": "milestone_draws",
                        "B1.4": "milestone_winning_tickets",
                    }[code]
                    await self.store(
                        code,
                        f"{code}:milestone:{threshold}",
                        at,
                        author,
                        {
                            placeholder: number(threshold),
                            "value": number(threshold),
                            "topic_hashtag": "#CasperДостижения",
                            "public_topic_hashtag": "#достижения",
                        },
                        payload={
                            "metric": rule.metric,
                            "threshold": threshold,
                            "observed_value": count,
                        },
                        historical=historical,
                    )

    async def _jackpot_records(
        self,
        start: datetime,
        end: datetime,
        author: Any,
        games: dict[Any, Any],
        names: dict[str, str],
        wins: list[Any],
        historical: bool,
    ) -> None:
        # Reconstruct snapshots at the agreed editorial scan times, using immutable
        # jackpot ledger movements rather than today's balance for a past event.
        movements = (
            await self.session.execute(
                select(LedgerTransaction)
                .where(
                    LedgerTransaction.account_kind == LedgerAccountKind.JACKPOT,
                    LedgerTransaction.created_at < end,
                )
                .order_by(LedgerTransaction.created_at, LedgerTransaction.id)
            )
        ).scalars()
        draw_formats = {
            identifier: format_key(snapshot)
            for identifier, snapshot in (
                await self.session.execute(select(Draw.id, Draw.configuration_snapshot))
            ).all()
        }
        grouped: dict[tuple[datetime, str, str], Any] = {}
        records: dict[str, int] = {}
        absolute = 0
        for move in movements:
            if move.lottery_id not in games:
                continue
            game = games[move.lottery_id].code
            if game == "daily":
                continue
            peak = max(move.balance_before, move.balance_after)
            record_key = game + ":" + draw_formats.get(move.draw_id, "initial")
            if move.created_at < start:
                records[record_key] = max(records.get(record_key, 0), peak)
                absolute = max(absolute, peak)
                continue
            local = move.created_at.astimezone(MOSCOW)
            slots = [
                local.replace(
                    hour=int(s[:2]), minute=int(s[3:]), second=0, microsecond=0
                )
                for s in event_config().scan_times
            ]
            slot = next(
                (s for s in slots if s >= local), slots[0] + timedelta(days=1)
            ).astimezone(UTC)
            slot = min(slot, end)
            existing = grouped.get((slot, game, record_key))
            if existing is None or peak > max(
                existing.balance_before, existing.balance_after
            ):
                grouped[(slot, game, record_key)] = move
        bases = {
            code: int(base)
            for code, base in (
                await self.session.execute(
                    select(Lottery.code, JackpotAccount.base_amount).join(
                        JackpotAccount, JackpotAccount.lottery_id == Lottery.id
                    )
                )
            ).all()
        }
        # Published/queued notices are editorial checkpoints. Tiny financial
        # records must not advance these, otherwise a 100m gap could never accrue.
        checkpoints: dict[str, int] = {}
        absolute_checkpoint = 0
        notices = await self.session.scalars(
            select(Publication).where(
                Publication.event_type.in_(["A1.3", "A1.4", "B2.1"]),
                or_(
                    Publication.content["delivery"]["state"].astext == "sent",
                    and_(
                        Publication.content["delivery"]["state"].astext == "queued",
                        publication_eligibility_filter(),
                    ),
                ),
            )
        )
        for notice in notices:
            payload = notice.content.get("event", {}).get("payload", {})
            value = int(payload.get("new_record", 0))
            if not value:
                # Older A1.4 notices carried the value in their stable event key.
                value = int((notice.event_key or "0").rsplit(":", 1)[-1])
            if notice.event_type == "A1.3":
                key = (notice.event_key or "").removeprefix("A1.3:").rsplit(":", 1)[0]
                checkpoints[key] = max(checkpoints.get(key, 0), value)
            else:
                absolute_checkpoint = max(absolute_checkpoint, value)
        for key, value in records.items():
            checkpoints.setdefault(key, value)
        absolute_checkpoint = absolute_checkpoint or absolute
        for (_, game, record_key), move in sorted(
            grouped.items(), key=lambda item: (item[1].created_at, item[1].id)
        ):
            peak = max(move.balance_before, move.balance_after)
            previous = records.get(record_key, bases.get(game, 0))
            records[record_key] = max(previous, peak)
            values = dict(
                game_name=names[game],
                jackpot_cas=number(peak),
                previous_record_cas=number(previous),
                value=f"{number(peak)} CAS",
                comparison_scope_label="в действующем формате игры",
                game_hashtag="#" + re.sub(r"\W", "", names[game]),
                topic_hashtag="#Рекорд",
                public_topic_hashtag="#джекпот",
            )
            checkpoint = checkpoints.get(record_key, previous)
            if peak > previous and jackpot_record_eligible(peak, checkpoint):
                row = await self.store(
                    "A1.3",
                    f"A1.3:{record_key}:{peak}",
                    move.created_at,
                    author,
                    {**values, "previous_record_cas": number(checkpoint)},
                    game=game,
                    payload={
                        "previous_record": previous,
                        "new_record": peak,
                        "publication_baseline": checkpoint,
                    },
                    historical=historical,
                )
                if row is not None:
                    checkpoints[record_key] = peak
            if peak > absolute:
                old_absolute = absolute
                absolute = peak
                if jackpot_record_eligible(peak, absolute_checkpoint):
                    payload = {
                        "new_record": peak,
                        "previous_record": old_absolute,
                        "publication_baseline": absolute_checkpoint,
                        "lottery_code": game,
                        "ledger_id": str(move.id),
                    }
                    await self.store(
                        "A1.4",
                        f"A1.4:{peak}",
                        move.created_at,
                        author,
                        {
                            **values,
                            "previous_record_cas": number(absolute_checkpoint),
                            "comparison_scope_label": "за всё время Casper Loto",
                        },
                        game=game,
                        payload=payload,
                        historical=historical,
                    )
                    await self.store(
                        "B2.1",
                        f"B2.1:record:{peak}",
                        move.created_at,
                        author,
                        {
                            **values,
                            "new_record_cas": number(peak),
                            "previous_record_cas": number(absolute_checkpoint),
                            "topic_hashtag": "#CasperРекорды",
                        },
                        payload=payload,
                        historical=historical,
                    )
                    absolute_checkpoint = peak
            # Individual bases may change; use the approved base captured by the
            # latest win/reset, otherwise the configured approved account base.
            earlier_wins = [
                w
                for w in wins
                if w.lottery_id == move.lottery_id and w.occurred_at <= move.created_at
            ]
            reset = earlier_wins[-1] if earlier_wins else None
            base = reset.base_jackpot_after if reset else bases.get(game, 0)
            if base:
                for numerator, denominator in self.rules["jackpot_multipliers"]:
                    threshold = (base * numerator + denominator - 1) // denominator
                    if peak >= threshold:
                        at_before = await self.session.scalar(
                            select(
                                func.max(
                                    func.greatest(
                                        LedgerTransaction.balance_before,
                                        LedgerTransaction.balance_after,
                                    )
                                )
                            ).where(
                                LedgerTransaction.account_kind
                                == LedgerAccountKind.JACKPOT,
                                LedgerTransaction.lottery_id == move.lottery_id,
                                LedgerTransaction.created_at
                                >= (
                                    reset.occurred_at
                                    if reset
                                    else datetime.min.replace(tzinfo=UTC)
                                ),
                                LedgerTransaction.created_at < start,
                            )
                        )
                        if int(at_before or 0) < threshold:
                            await self.store(
                                "A1.2",
                                "A1.2:"
                                + game
                                + ":"
                                + str(reset.id if reset else "origin")
                                + ":"
                                + str(threshold),
                                move.created_at,
                                author,
                                {
                                    **values,
                                    "milestone_cas": number(threshold),
                                    "next_draw_moscow": moscow(
                                        await self.session.scalar(
                                            select(Draw.scheduled_at)
                                            .where(
                                                Draw.lottery_id == move.lottery_id,
                                                Draw.scheduled_at > move.created_at,
                                            )
                                            .order_by(Draw.scheduled_at)
                                            .limit(1)
                                        )
                                        or move.created_at
                                    ),
                                    "topic_hashtag": "#Джекпот",
                                },
                                game=game,
                                historical=historical,
                            )


async def deliver_one(
    factory: async_sessionmaker[AsyncSession],
    bot: Any,
    *,
    now: datetime,
    assets: Path = Path("/app/publication-assets"),
    fonts: Path = Path("/usr/share/fonts/truetype/dejavu"),
) -> str:
    """Claim once; Telegram's definitive 429 is the only automatically retried send."""
    from k_loto.application.publication_retention import stale_streak_filter

    async with factory() as session, session.begin():
        engine = PublicationEventService(session)
        await engine._lock()
        state = await engine._state("publication.transport")
        if not state.value.get("enabled"):
            return "disabled"
        interrupted = await session.scalars(
            select(Publication)
            .where(
                Publication.status == "draft",
                Publication.content["delivery"]["state"].astext == "sending",
            )
            .with_for_update()
        )
        for pending in interrupted:
            attempted = pending.content["delivery"].get("attempted_at")
            if attempted and datetime.fromisoformat(attempted) > now - timedelta(
                minutes=5
            ):
                continue
            content = deepcopy(pending.content)
            content["delivery"].update(
                state="uncertain", error_type="InterruptedDelivery"
            )
            pending.content = content
        unresolved = await session.scalar(
            select(Publication.id)
            .where(
                Publication.status == "draft",
                Publication.content["delivery"]["state"].astext.in_(
                    ["sending", "uncertain"]
                ),
            )
            .limit(1)
        )
        if unresolved:
            return "uncertain"
        row = await session.scalar(
            select(Publication)
            .where(
                Publication.status == "draft",
                Publication.content["delivery"]["state"].astext == "queued",
                publication_eligibility_filter(),
                ~stale_streak_filter(),
            )
            .order_by(
                Publication.content["event"]["occurred_at"].astext, Publication.id
            )
            .limit(1)
            .with_for_update()
        )
        if row is None:
            return "empty"
        delivery = row.content["delivery"]
        if (
            delivery.get("retry_after")
            and datetime.fromisoformat(delivery["retry_after"]) > now
        ):
            return "throttled"
        if (
            not delivery.get("historical")
            and not delivery.get("manual")
            and state.value.get("last_automatic_sent_at")
            and now
            < datetime.fromisoformat(state.value["last_automatic_sent_at"])
            + timedelta(seconds=event_config().delivery.minimum_interval_seconds)
        ):
            return "interval"
        # Rendering errors happen before any network side effect or claim.
        try:
            content = editorial_snapshot(row.content, row.lottery_code)
            image = await asyncio.to_thread(
                render_post, content, assets=assets, fonts=fonts
            )
            caption = caption_html(content["channel_caption"])
        except Exception as error:
            content = deepcopy(row.content)
            content["delivery"].update(state="failed", error_type=type(error).__name__)
            row.content = content
            return "failed"
        identifier = row.id
        content["delivery"].update(state="sending", attempted_at=now.isoformat())
        row.content = content
    try:
        async with asyncio.timeout(60):
            message = await bot.send_photo(
                get_settings().publication_channel,
                photo=BufferedInputFile(image, filename=f"casper-{identifier}.png"),
                caption=caption,
                parse_mode="HTML",
            )
    except TelegramRetryAfter as error:
        async with factory() as session, session.begin():
            row = await session.get(Publication, identifier, with_for_update=True)
            assert row is not None
            content = deepcopy(row.content)
            content["delivery"].update(
                state="queued",
                retry_after=(
                    datetime.now(UTC) + timedelta(seconds=error.retry_after)
                ).isoformat(),
            )
            row.content = content
        return "throttled"
    except Exception as error:
        async with factory() as session, session.begin():
            row = await session.get(Publication, identifier, with_for_update=True)
            assert row is not None
            content = deepcopy(row.content)
            content["delivery"].update(
                state="uncertain", error_type=type(error).__name__
            )
            row.content = content
        return "uncertain"
    async with factory() as session, session.begin():
        row = await session.get(Publication, identifier, with_for_update=True)
        assert row is not None
        content = deepcopy(row.content)
        content["delivery"].update(
            state="sent",
            message_id=message.message_id,
            channel_id=message.chat.id,
            sent_at=datetime.now(UTC).isoformat(),
        )
        row.content = content
        row.status = "published"
        row.published_at = datetime.now(UTC)
        row.revision += 1
        state = await PublicationEventService(session)._state("publication.transport")
        if not content["delivery"].get("historical") and not content["delivery"].get(
            "manual"
        ):
            state.value = {
                **state.value,
                "last_automatic_sent_at": row.published_at.isoformat(),
            }
    return "sent"


async def drain(factory: async_sessionmaker[AsyncSession]) -> None:
    settings = get_settings()
    if not settings.lottery_bot_token or not settings.publication_channel:
        return
    bot = Bot(settings.lottery_bot_token.get_secret_value())
    try:
        while await deliver_one(factory, bot, now=datetime.now(UTC)) == "sent":
            pass
    finally:
        await bot.session.close()
