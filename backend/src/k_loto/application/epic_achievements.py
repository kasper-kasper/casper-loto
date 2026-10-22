"""Approved 17 epic definitions, funded gifts and planned case quantities."""

from k_loto.application.achievement_catalog import CatalogEntry


def epic_catalog() -> list[CatalogEntry]:
    def count(metric: str, target: int, **filters: object) -> dict[str, object]:
        return {"metric": metric, "target": target, **filters}

    def result(lottery: str, target: int = 1, **filters: object) -> dict[str, object]:
        return count("result_count", target, lottery=lottery, **filters)

    # code, title, condition copy, flavor, icon, conditions, CAS, game, tickets, cases
    rows = [
        (
            "fifteen_thousand_tickets",
            "Ветеран Каспера",
            "Купить суммарно 15 000 платных билетов",
            "Пятнадцать тысяч билетов. Кажется, ты знаешь здесь каждый уголок!",
            "tickets",
            [count("paid_tickets", 15_000)],
            6_000_000,
            "weekly",
            10,
            4,
        ),
        (
            "thousand_wins",
            "Любимчик фортуны",
            "Получить 1 000 выигрышных платных билетов",
            "Тысяча побед! Удача уже здоровается с тобой за руку.",
            "clover",
            [count("winning_tickets", 1000)],
            6_000_000,
            "pss",
            10,
            4,
        ),
        (
            "classic_five",
            "Шаг до легенды",
            "Угадать ровно 5 чисел в «6 из 36» по платному билету",
            "Пять из шести. До легенды оставался всего один шаг!",
            "clover",
            [result("khan", matches=5)],
            4_000_000,
            "khan",
            10,
            4,
        ),
        (
            "ball_five_zero",
            "Потерянный шар",
            "Получить призовую комбинацию 5+0 в Casper Ball по платному билету",
            "Пять шаров на месте. А последний где-то гуляет!",
            "circle-dot",
            [result("pss", primary_matches=5, secondary_matches=0, min_prize=1)],
            6_000_000,
            "pss",
            10,
            4,
        ),
        (
            "grand_near_crown",
            "Почти король",
            "Получить призовую комбинацию 5+0 или 5+1 в Casper Grand "
            "по платному билету",
            "Корона уже близко. Осталось совсем чуть-чуть!",
            "castle",
            [
                result("weekly", primary_matches=5, secondary_matches=0, min_prize=1),
                result("weekly", primary_matches=5, secondary_matches=1, min_prize=1),
            ],
            8_000_000,
            "weekly",
            10,
            4,
        ),
        (
            "fourteen_winning_games",
            "Мастер четырнадцати",
            "Получить выигрыш по платному билету в 14 разных лотереях, "
            "включая мгновенные",
            "Четырнадцать лотерей, четырнадцать побед. Да ты универсал!",
            "map-pinned",
            [count("winning_lotteries", 14)],
            8_000_000,
            "bingo",
            10,
            4,
        ),
        (
            "ten_tenfold_wins",
            "Большая коллекция",
            "Получить 10 выигрышей по разным платным билетам, "
            "каждый не меньше 10 цен своего билета",
            "Десять солидных выигрышей. Красиво собрал коллекцию!",
            "hand-coins",
            [count("qualifying_wins", 10, multiplier_numerator=10)],
            3_000_000,
            "weekly",
            5,
            1,
        ),
        (
            "hundred_thousand_tickets",
            "Тут всё моё",
            "Купить суммарно 100 000 платных билетов",
            "Сто тысяч билетов. Ты тут уже всё выкупил?",
            "package-open",
            [count("paid_tickets", 100_000)],
            20_000_000,
            "weekly",
            10,
            4,
        ),
        (
            "fifty_day_streak",
            "Ты ещё здесь?!",
            "Открывать приложение 50 календарных дней подряд по Москве",
            "Пятьдесят дней подряд?! Мы уже начали волноваться, когда тебя не видно.",
            "calendar-heart",
            [count("max_streak", 50)],
            4_000_000,
            "september",
            10,
            4,
        ),
        (
            "hundred_days",
            "Старые знакомые",
            "Открыть приложение в 100 разных календарных дней по Москве",
            "Сто встреч. Нам уже и представляться не нужно.",
            "calendar-heart",
            [count("active_days", 100)],
            4_000_000,
            "pll",
            10,
            4,
        ),
        (
            "hundred_million_prizes",
            "Теперь серьёзно",
            "Накопить 100 000 000 CAS призовых выплат по платным билетам",
            "Сто миллионов призовых CAS. Тут уже без шуток!",
            "coins",
            [count("won_cas", 100_000_000)],
            6_000_000,
            "weekly",
            10,
            4,
        ),
        (
            "code_four_thrice",
            "Тройной взлом",
            "Трижды угадать ровно 4 позиции из 5 в CODE по разным платным билетам",
            "Три взлома. Кажется, пора менять пароли!",
            "fingerprint",
            [result("shadow", 3, matches=4)],
            3_500_000,
            "pll",
            10,
            4,
        ),
        (
            "flash_four_five_times",
            "Молния дважды не бьёт?",
            "Пять раз угадать ровно 4 числа в FLASH по разным платным билетам",
            "Пять разрядов! Кажется, молния выбрала тебя.",
            "zap",
            [result("flash", 5, matches=4)],
            3_500_000,
            "grob",
            10,
            4,
        ),
        (
            "pulse_two_two_twice",
            "Кардиограмма",
            "Дважды получить 2+2 в PULSE по разным платным билетам, с любым шифром",
            "Два идеальных импульса. Кардиолог бы удивился!",
            "flame",
            [result("pulse", 2, primary_matches=2, secondary_matches=2)],
            5_000_000,
            "weekly",
            10,
            4,
        ),
        (
            "dual_mixed_thrice",
            "Две стороны медали",
            "Трижды суммарно получить призовые комбинации 1+2 или 2+1 "
            "в Casper Dual по разным платным билетам",
            "Трижды нашёл баланс. Между прочим, не каждому дано!",
            "eclipse",
            [result("dual", 3, matches_any=[12, 21], min_prize=1)],
            3_500_000,
            "pss",
            10,
            4,
        ),
        (
            "five_consecutive_wins",
            "Без права на ошибку",
            "Выиграть по платным билетам в 5 соседних завершённых тиражах "
            "одной лотереи",
            "Пять тиражей подряд с выигрышем. Это было красиво!",
            "history",
            [count("consecutive_winning_draws", 5)],
            5_000_000,
            "weekly",
            10,
            4,
        ),
        (
            "five_daily_winning_games",
            "Человек-оркестр",
            "Выиграть по платным билетам в 5 разных лотереях за один день по Москве",
            "Пять лотерей, пять побед. Сегодня ты дирижируешь удачей!",
            "compass",
            [count("daily_winning_lotteries", 5)],
            3_000_000,
            "khan",
            10,
            1,
        ),
    ]
    entries = []
    for position, (
        code,
        title,
        description,
        flavor,
        icon,
        conditions,
        cash,
        game,
        amount,
        cases,
    ) in enumerate(rows):
        rewards = [{"type": "cas", "amount": cash}]
        rewards.extend(
            {"type": "ticket", "lottery": game, "amount": 1} for _ in range(amount)
        )
        rewards.append({"type": "case", "amount": cases, "planned": True})
        entries.append(
            CatalogEntry.model_validate(
                {
                    "code": f"epic_{code}",
                    "version": 1,
                    "rarity": "epic",
                    "title": title,
                    "description": description,
                    "flavor": flavor,
                    "icon": icon,
                    "active": True,
                    "sort_order": 300 + position,
                    "condition": {"mode": "any", "conditions": conditions},
                    "rewards": rewards,
                }
            )
        )
    return entries
