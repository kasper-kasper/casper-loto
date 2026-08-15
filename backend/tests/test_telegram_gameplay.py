"""Full Telegram gameplay menu, selection and player projection tests."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.bot_gameplay import (
    BotDraw,
    BotHome,
    BotLotteryCard,
    BotPlayer,
    BotPlayerStatistics,
    BotTicket,
    TelegramGameplayQueryService,
)
from k_loto.domain.enums import (
    DrawStatus,
    LedgerAccountKind,
    LotteryKind,
    TicketStatus,
    TransactionType,
)
from k_loto.infrastructure.database.models import (
    Draw,
    LedgerTransaction,
    Lottery,
    Ticket,
    User,
)
from k_loto.infrastructure.telegram_game_ui import (
    add_daily_to_cart,
    add_weekly_to_cart,
    daily_picker_markup,
    format_draws,
    format_home,
    format_picker,
    format_statistics,
    format_tickets,
    lottery_menu_markup,
    main_menu_markup,
    rules_text,
    telegram_checkout_idempotency_key,
    toggle_daily_number,
    toggle_weekly_number,
    weekly_picker_markup,
)


class ExecuteResult:
    def __init__(self, *, one: Any = None, rows: list[Any] | None = None) -> None:
        self._one = one
        self._rows = rows or []

    def one_or_none(self) -> Any:
        return self._one

    def all(self) -> list[Any]:
        return self._rows


class ScalarResult:
    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def all(self) -> list[Any]:
        return self._values


class FakeSession:
    def __init__(
        self,
        *,
        execute_results: list[ExecuteResult],
        scalar_results: list[ScalarResult] | None = None,
        scalar_values: list[Any] | None = None,
    ) -> None:
        self._execute_results = iter(execute_results)
        self._scalar_results = iter(scalar_results or [])
        self._scalar_values = iter(scalar_values or [])

    async def execute(self, _statement: object) -> ExecuteResult:
        return next(self._execute_results)

    async def scalars(self, _statement: object) -> ScalarResult:
        return next(self._scalar_results)

    async def scalar(self, _statement: object) -> Any:
        return next(self._scalar_values)


def callback_values(markup: Any) -> set[str]:
    return {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data
    }


def test_main_menu_exposes_complete_gameplay_navigation() -> None:
    assert callback_values(main_menu_markup()) == {
        "bot:buy",
        "bot:balance",
        "bot:tickets:active",
        "bot:results",
        "bot:statistics",
        "bot:rules",
    }
    assert callback_values(lottery_menu_markup()) == {
        "game:weekly",
        "game:daily",
        "bot:home",
    }


def test_weekly_picker_selects_exactly_five_unique_numbers() -> None:
    selected: tuple[int, ...] = ()
    for number in [5, 1, 20, 7, 12]:
        selected = toggle_weekly_number(selected, number)

    assert selected == (1, 5, 7, 12, 20)
    with pytest.raises(ValueError, match="five"):
        toggle_weekly_number(selected, 9)
    assert toggle_weekly_number(selected, 7) == (1, 5, 12, 20)
    with pytest.raises(ValueError, match="between"):
        toggle_weekly_number((), 21)


def test_daily_picker_selects_four_of_fifteen_and_supports_cart() -> None:
    selected: tuple[int, ...] = ()
    for number in (15, 1, 7, 4):
        selected = toggle_daily_number(selected, number)
    assert selected == (1, 4, 7, 15)
    assert add_daily_to_cart((), selected, maximum=2) == (selected,)
    callbacks = callback_values(daily_picker_markup(selected, 0))
    assert {f"pick:{value}" for value in range(1, 16)}.issubset(callbacks)
    with pytest.raises(ValueError):
        toggle_daily_number(selected, 2)


def test_weekly_cart_allows_identical_tickets_and_enforces_transport_limit() -> None:
    ticket = (1, 2, 3, 4, 5)
    cart = add_weekly_to_cart((), ticket, maximum=2)
    cart = add_weekly_to_cart(cart, ticket, maximum=2)

    assert cart == (ticket, ticket)
    with pytest.raises(ValueError, match="up to 2"):
        add_weekly_to_cart(cart, ticket, maximum=2)
    with pytest.raises(ValueError, match="exactly five"):
        add_weekly_to_cart((), (1, 2), maximum=2)


def test_picker_keyboard_contains_all_numbers_and_checkout_controls() -> None:
    markup = weekly_picker_markup((1, 20), 2)
    callbacks = callback_values(markup)

    assert {f"pick:{number}" for number in range(1, 21)}.issubset(callbacks)
    assert {"pick:random", "pick:clear", "pick:add", "pick:checkout"}.issubset(
        callbacks
    )
    labels = [button.text for row in markup.inline_keyboard for button in row]
    assert "✓ 01" in labels
    assert "✓ 20" in labels
    assert "✅ Купить (2)" in labels


def test_telegram_checkout_idempotency_key_is_stable_and_scoped() -> None:
    first = telegram_checkout_idempotency_key(123, "cart-session")

    assert first == telegram_checkout_idempotency_key(123, "cart-session")
    assert first != telegram_checkout_idempotency_key(124, "cart-session")
    with pytest.raises(ValueError):
        telegram_checkout_idempotency_key(0, "cart-session")


def test_gameplay_formatters_show_server_values_and_rules() -> None:
    now = datetime(2026, 8, 16, 17, tzinfo=UTC)
    home = BotHome(
        BotPlayer(UUID(int=1), "Player", 5_000),
        2,
        (
            BotLotteryCard(
                UUID(int=2),
                "weekly",
                "Weekly 5/20",
                5,
                20,
                100,
                10_000,
                7,
                now,
                now - timedelta(minutes=5),
                True,
            ),
        ),
    )
    ticket = BotTicket(
        10,
        "Weekly 5/20",
        7,
        now,
        (1, 2, 3, 4, 5),
        100,
        TicketStatus.SETTLED,
        3,
        100,
        (1, 2, 3, 8, 9),
    )
    draw = BotDraw(
        "Weekly 5/20", 7, now, now, (1, 2, 3, 8, 9), 12, 1_200, 300, 10_600, 0
    )
    stats = BotPlayerStatistics(4, 400, 100, -300, 100, 3, {0: 1, 3: 1})

    assert "Баланс: 5 000 CAS" in format_home(home)
    assert "Корзина" in format_picker(
        selected=(1, 2, 3, 4, 5), cart=((5, 6, 7, 8, 9),), price=100
    )
    assert "Совпадений: 3" in format_tickets((ticket,), active=False)
    assert "Переходящий jackpot: 10 600 CAS" in format_draws((draw,))
    assert "Итог: -300 CAS" in format_statistics(stats)
    assert "19:55 MSK" in rules_text()
    assert "Daily 4 из 15" in rules_text()
    assert "за 2 минуты" in rules_text()


async def test_home_projection_uses_database_balance_funds_and_next_draw() -> None:
    now = datetime(2026, 8, 16, 12, tzinfo=UTC)
    user = User(
        id=UUID(int=80),
        telegram_id=123,
        username="player",
        display_name="Player",
        is_active=True,
        is_admin=False,
    )
    lottery = Lottery(
        id=UUID(int=81),
        code="weekly",
        name="Weekly 5/20",
        kind=LotteryKind.WEEKLY,
        numbers_to_pick=5,
        max_number=20,
        ticket_price=100,
        timezone="Europe/Moscow",
        schedule={"weekday": "sunday"},
        sales_cutoff_minutes=5,
        is_active=True,
        next_draw_number=8,
        next_ticket_number=10,
    )
    draw = Draw(
        id=UUID(int=82),
        lottery_id=lottery.id,
        public_number=7,
        status=DrawStatus.SCHEDULED,
        scheduled_at=now + timedelta(hours=5),
        sales_close_at=now + timedelta(hours=4, minutes=55),
        correlation_id=UUID(int=83),
        ticket_count=2,
        total_sales=200,
        total_payout=0,
        reserve_used=0,
    )
    fake = FakeSession(
        execute_results=[
            ExecuteResult(one=(user, 5_000)),
            ExecuteResult(rows=[(lottery, 12_000)]),
        ],
        scalar_values=[2, draw],
    )

    home = await TelegramGameplayQueryService(cast(AsyncSession, fake)).home(
        123, now=now
    )

    assert home.player.balance == 5_000
    assert home.active_ticket_count == 2
    assert home.lotteries[0].jackpot == 12_000
    assert home.lotteries[0].draw_number == 7
    assert home.lotteries[0].purchase_available


async def test_player_statistics_are_derived_from_tickets_and_ledger() -> None:
    user_id = UUID(int=50)
    user = User(
        id=user_id,
        telegram_id=123,
        username="player",
        display_name="Player",
        is_active=True,
        is_admin=False,
    )
    tickets = [
        Ticket(
            id=UUID(int=51),
            public_number=1,
            lottery_id=UUID(int=60),
            draw_id=UUID(int=61),
            user_id=user_id,
            numbers=[1, 2, 3, 4, 5],
            purchase_price=100,
            status=TicketStatus.SETTLED,
            matches=2,
            prize_amount=25,
        ),
        Ticket(
            id=UUID(int=52),
            public_number=2,
            lottery_id=UUID(int=60),
            draw_id=UUID(int=61),
            user_id=user_id,
            numbers=[6, 7, 8, 9, 10],
            purchase_price=100,
            status=TicketStatus.SETTLED,
            matches=5,
            prize_amount=1_000,
        ),
    ]
    ledger = [
        LedgerTransaction(
            id=UUID(int=70),
            operation_id=UUID(int=71),
            idempotency_key="purchase",
            account_kind=LedgerAccountKind.USER_BALANCE,
            account_id=user_id,
            type=TransactionType.TICKET_PURCHASE,
            amount=-200,
            balance_before=2_000,
            balance_after=1_800,
            user_id=user_id,
            details={},
        ),
        LedgerTransaction(
            id=UUID(int=72),
            operation_id=UUID(int=73),
            idempotency_key="payout",
            account_kind=LedgerAccountKind.USER_BALANCE,
            account_id=user_id,
            type=TransactionType.JACKPOT_PAYOUT,
            amount=1_025,
            balance_before=1_800,
            balance_after=2_825,
            user_id=user_id,
            details={},
        ),
    ]
    fake = FakeSession(
        execute_results=[ExecuteResult(one=(user, 2_825))],
        scalar_results=[ScalarResult(tickets), ScalarResult(ledger)],
    )

    stats = await TelegramGameplayQueryService(cast(AsyncSession, fake)).statistics(123)

    assert stats.ticket_count == 2
    assert (stats.spent, stats.won, stats.net) == (200, 1_025, 825)
    assert (stats.best_prize, stats.best_matches) == (1_000, 5)
    assert stats.match_counts[2] == 1
    assert stats.match_counts[5] == 1
