"""Owner-approved jackpot collection; ten fixed base awards and one final award."""

from k_loto.application.achievement_catalog import CatalogEntry

# Ordered by the owner's original list. Ticket packages never include Dual.
LEGENDARY_ROWS = (
    (
        "flash",
        "Удар молнии",
        "Пять из пяти. Кажется, молния попала точно в тебя!",
        "Угадать 5 чисел из 20",
        40_000_000,
        200,
        40,
    ),
    (
        "shadow",
        "Код принят!",
        "Код совпал. Шифр разгадан. Доступ к легендам разрешён!",
        "Угадать все 5 цифр CODE на своих позициях",
        60_000_000,
        300,
        60,
    ),
    (
        "pulse",
        "Сердце Каспера",
        "Пульс зашкаливает. Даже Каспер почувствовал!",
        "Угадать 2 из 12, 2 из 6 и автоматический шифр 001–199",
        90_000_000,
        350,
        70,
    ),
    (
        "khan",
        "Шесть из шести",
        "Шесть чисел. Шесть попаданий. Добро пожаловать в историю Каспера!",
        "Угадать все 6 чисел из 36",
        150_000_000,
        400,
        80,
    ),
    (
        "pss",
        "Последний звонок",
        "Этот звонок ты запомнишь надолго. Каспер звонит лично тебе!",
        "Угадать 5 чисел из 36 и дополнительный шар из 8",
        220_000_000,
        450,
        90,
    ),
    (
        "weekly",
        "Ваше величество",
        "Корона твоя. Сегодня в Casper Grand появился новый король!",
        "Угадать 5 чисел из 35 и 2 дополнительных числа из 5",
        350_000_000,
        500,
        100,
    ),
    (
        "bingo",
        "Легендарное БИНГООО",
        "Это БИНГО, которое войдёт в историю!",
        "Закрыть все 12 чисел карточки не позднее 28-го хода",
        90_000_000,
        250,
        50,
    ),
    (
        "pll",
        "Время пришло",
        "2.22, это время неизбежно.",
        "Угадать 4 числа из 15",
        40_000_000,
        100,
        20,
    ),
    (
        "september",
        "Календарь на репите",
        "Та самая дата, та самая песня. Только теперь у тебя ещё и джекпот!",
        "Угадать 3 числа из 33",
        50_000_000,
        150,
        30,
    ),
    (
        "grob",
        "Бу! Испугался?",
        "Даже привидения не ожидали такого исхода!",
        "Угадать 3 числа из 28",
        40_000_000,
        125,
        25,
    ),
)
LEGENDARY_CODES = tuple(f"legendary_{row[0]}_jackpot" for row in LEGENDARY_ROWS)
MASTER_CODE = "legendary_casper_move_over"


def legendary_catalog() -> list[CatalogEntry]:
    entries = []
    for i, (game, title, flavor, description, cash, tickets, cases) in enumerate(
        LEGENDARY_ROWS
    ):
        condition = {
            "metric": "result_count",
            "target": 1,
            "lottery": game,
            "natural_jackpot": True,
            "min_prize": 1,
        }
        exact = {
            "flash": 5,
            "shadow": 5,
            "pulse": 221,
            "khan": 6,
            "pll": 4,
            "september": 3,
            "grob": 3,
            "bingo": 12,
        }
        if game in exact:
            condition["matches"] = exact[game]
        if game in {"pss", "weekly"}:
            condition["primary_matches"] = 5
            condition["secondary_matches"] = 1 if game == "pss" else 2
        if game == "bingo":
            condition["bingo_full_move_lte"] = 28
        entries.append(
            CatalogEntry.model_validate(
                dict(
                    code=LEGENDARY_CODES[i],
                    version=1,
                    rarity="legendary",
                    title=title,
                    description=description
                    + " по оплаченному билету с подтверждённой выплатой джекпота",
                    flavor=flavor,
                    active=True,
                    sort_order=400 + i,
                    icon=f"lottery:{game}",
                    condition={"conditions": [condition]},
                    rewards=[
                        {"type": "cas", "amount": cash},
                        {"type": "cosmetic", "item": f"badge:{game}"},
                        {"type": "cosmetic", "item": "theme:gold"},
                        {"type": "ticket_pack", "lottery": game, "amount": tickets},
                        {"type": "case", "amount": cases, "planned": True},
                    ],
                )
            )
        )
    entries.append(
        CatalogEntry.model_validate(
            dict(
                code=MASTER_CODE,
                version=1,
                rarity="legendary",
                title="Каспер, подвинься",
                description="Получить все 10 исходных легендарных достижений "
                "за джекпоты разных лотерей",
                flavor="Все десять джекпотов. Каспер, кажется, уступает тебе место.",
                active=True,
                sort_order=410,
                icon="casper-master",
                condition={
                    "conditions": [
                        {
                            "metric": "earned_set",
                            "target": 10,
                            "achievement_codes": list(LEGENDARY_CODES),
                        }
                    ]
                },
                rewards=[
                    {"type": "cas", "amount": 1_000_000_000},
                    {"type": "cosmetic", "item": "badge:casper-master"},
                    {"type": "cosmetic", "item": "theme:beyond"},
                    *[
                        {"type": "ticket_pack", "lottery": row[0], "amount": 300}
                        for row in LEGENDARY_ROWS
                    ],
                    {"type": "case", "amount": 200, "planned": True},
                ],
            )
        )
    )
    return entries
