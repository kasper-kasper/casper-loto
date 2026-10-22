"""The owner's approved first catalog and fund-backed rewards, local only."""

from k_loto.application.achievement_catalog import CatalogEntry

CAS_AMOUNTS = (
    20_000,
    30_000,
    25_000,
    40_000,
    50_000,
    100_000,
    60_000,
    100_000,
    40_000,
    100_000,
    20_000,
    20_000,
    30_000,
    30_000,
    30_000,
    40_000,
    30_000,
    40_000,
    30_000,
    25_000,
    50_000,
    20_000,
)
TICKET_REWARDS = {
    "first_profit": "september",
    "ten_tickets": "grob",
    "twenty_five_tickets": "pll",
    "ten_wins": "pss",
    "three_games": "september",
    "seven_games": "khan",
    "three_days": "september",
    "bulk_purchase": "grob",
}
CASE_REWARDS = {"twenty_five_tickets", "ten_wins", "seven_games", "three_days"}


def common_catalog() -> list[CatalogEntry]:
    def count(metric: str, target: int = 1, **filters: object) -> dict[str, object]:
        return {"metric": metric, "target": target, **filters}

    def games(*codes: str) -> list[dict[str, object]]:
        return [count("paid_tickets", lottery=code) for code in codes]

    rows = [
        (
            "first_ticket",
            "Ты с нами!",
            "Купить первый платный билет",
            "ticket-check",
            [count("paid_tickets")],
        ),
        (
            "first_win",
            "Опа, прилетело!",
            "Получить первый выигрыш по платному билету",
            "coins",
            [count("winning_tickets")],
        ),
        (
            "break_even",
            "Ну хоть не в минус",
            "Получить выплату ровно в стоимость платного билета",
            "wallet",
            [count("qualifying_wins", payout_vs_price="eq")],
        ),
        (
            "first_profit",
            "Почти богач",
            "Получить выплату больше стоимости платного билета",
            "trending-up",
            [count("qualifying_wins", payout_vs_price="gt")],
        ),
        (
            "ten_tickets",
            "Затянуло",
            "Купить 10 платных билетов суммарно",
            "tickets",
            [count("paid_tickets", 10)],
        ),
        (
            "twenty_five_tickets",
            "Тебе точно норм?",
            "Купить 25 платных билетов суммарно",
            "tickets",
            [count("paid_tickets", 25)],
        ),
        (
            "five_wins",
            "Пошла жара!",
            "Получить 5 выигрышных платных билетов",
            "flame",
            [count("winning_tickets", 5)],
        ),
        (
            "ten_wins",
            "Это уже система",
            "Получить 10 выигрышных платных билетов",
            "trophy",
            [count("winning_tickets", 10)],
        ),
        (
            "three_games",
            "Чё тут у вас?",
            "Купить билеты в 3 разных лотереях",
            "compass",
            [count("lotteries_count", 3)],
        ),
        (
            "seven_games",
            "Везде отметился",
            "Купить билеты в 7 разных лотереях",
            "compass",
            [count("lotteries_count", 7)],
        ),
        (
            "first_fast",
            "Вот это скорость!",
            "Купить первый платный билет Casper FAST",
            "zap",
            games("flash", "shadow", "pulse"),
        ),
        (
            "first_instant",
            "Здесь и сейчас",
            "Впервые сыграть в платную мгновенную игру",
            "clock-3",
            games("kasper-live", "aurora", "vault"),
        ),
        (
            "first_custom",
            "Особый случай",
            "Купить билет «3 сентября», «2:22» или Halloween",
            "star",
            games("september", "pll", "grob"),
        ),
        (
            "first_classic",
            "Как раньше",
            "Купить первый платный билет «6 из 36»",
            "history",
            games("khan"),
        ),
        (
            "first_ball",
            "Ну, покатились!",
            "Купить первый платный билет Casper Ball",
            "circle-dot",
            games("pss"),
        ),
        (
            "first_grand",
            "Играем по-крупному",
            "Купить первый платный билет Casper Grand",
            "crown",
            games("weekly"),
        ),
        (
            "first_dual",
            "И вашим, и нашим",
            "Купить первый платный билет Casper Dual",
            "split",
            games("dual"),
        ),
        (
            "first_bingo",
            "БИНГООО",
            "Купить первую платную карточку Casper Bingo",
            "grid-3x3",
            games("bingo"),
        ),
        (
            "three_days",
            "Ну наконец-то",
            "Открыть приложение в 3 разных дня по Москве",
            "calendar-check",
            [count("active_days", 3)],
        ),
        (
            "own_combination",
            "Я сам решу!",
            "Вручную выбрать всю комбинацию и оплатить билет",
            "list-ordered",
            [count("manual_tickets")],
        ),
        (
            "bulk_purchase",
            "Заверните всё!",
            "Купить не менее 5 платных билетов одной операцией",
            "shopping-bag",
            [count("bulk_purchases")],
        ),
        (
            "first_achievement_reward",
            "А так можно было?!",
            "Получить первую награду CAS за другое достижение",
            "gift",
            [count("rewarded_achievements")],
        ),
    ]
    return [
        CatalogEntry.model_validate(
            {
                "code": code,
                "version": 2,
                "rarity": "common",
                "title": title,
                "description": description,
                "icon": icon,
                "active": True,
                "sort_order": position,
                "reward_pending": False,
                "rewards": [
                    {"type": "cas", "amount": CAS_AMOUNTS[position]},
                    *(
                        [
                            {
                                "type": "ticket",
                                "lottery": TICKET_REWARDS[code],
                                "amount": 1,
                            }
                        ]
                        if code in TICKET_REWARDS
                        else []
                    ),
                    *(
                        [{"type": "case", "amount": 1, "planned": True}]
                        if code in CASE_REWARDS
                        else []
                    ),
                ],
                "condition": {"mode": "any", "conditions": conditions},
            }
        )
        for position, (code, title, description, icon, conditions) in enumerate(rows)
    ]
