"""Reproduce the read-only economy review; never connects to production."""

import json
from fractions import Fraction as F
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
snapshot = json.loads((HERE / "current-settings.json").read_text(encoding="utf-8"))


def matches(n, k, m):
    return F(comb(k, m) * comb(n - k, k - m), comb(n, k))


proposals = {
    "pll": (20_000, 10_000_000),
    "september": (3_333, 10_000_000),
    "grob": (6_666, 6_666_666),
    "flash": (2_000, 10_000_000),
    "shadow": (2_000, 10_000_000),
    "pulse": (2_500, 50_000_000),
    "khan": (25_000, 100_000_000),
    "pss": (25_000, 250_000_000),
    "weekly": (50_000, 1_000_000_000),
    "bingo": (50_000, 1_000_000_000),
    "dual": (20_000, 5_000_000),
}

rows = []
candidate_fixed_tiers = {
    "pss": {
        1: 25_000,
        11: 50_000,
        21: 100_000,
        31: 500_000,
        20: 25_000,
        30: 250_000,
        40: 1_000_000,
        41: 5_000_000,
        50: 25_000_000,
    },
    "weekly": {
        21: 150_000,
        22: 150_000,
        30: 300_000,
        31: 600_000,
        32: 900_000,
        40: 1_500_000,
        41: 3_000_000,
        42: 9_000_000,
        50: 30_000_000,
        51: 60_000_000,
    },
    "khan": {2: 12_500, 3: 75_000, 4: 750_000, 5: 7_500_000},
}
for game in snapshot["lotteries"]:
    if not game["is_active"]:
        continue
    code, rules = game["code"], game["rules"]
    price = game["ticket_price"]

    def expectation(at_price, *, candidate=False, code=code, rules=rules):
        if code == "dual":
            if candidate:
                return F(45_000_000, 4356), F(1, 4356)
            return F(13_000_000, 4356), F(1, 4356)
        if code == "bingo":
            p1 = (
                3 * F(comb(18, 4), comb(60, 4))
                - 3 * F(comb(18, 8), comb(60, 8))
                + F(comb(18, 12), comb(60, 12))
            )
            p2 = 3 * F(comb(34, 8), comb(60, 8)) - 2 * F(comb(34, 12), comb(60, 12))
            return 100_000 * p1 + 500_000 * p2, F(comb(28, 12), comb(60, 12))
        probabilities = {}
        if code == "shadow":
            probabilities = {i: F(comb(5, i) * 9 ** (5 - i), 100_000) for i in range(6)}
        elif rules["primary_numbers_to_pick"] is not None:
            for a in range(rules["primary_numbers_to_pick"] + 1):
                for b in range(rules["secondary_numbers_to_pick"] + 1):
                    p = matches(
                        rules["primary_max_number"], rules["primary_numbers_to_pick"], a
                    ) * matches(
                        rules["secondary_max_number"],
                        rules["secondary_numbers_to_pick"],
                        b,
                    )
                    if code == "pulse":
                        probabilities[a * 100 + b * 10] = p * F(198, 199)
                        probabilities[a * 100 + b * 10 + 1] = p * F(1, 199)
                    else:
                        probabilities[a * 10 + b] = p
        else:
            probabilities = {
                m: matches(rules["max_number"], rules["numbers_to_pick"], m)
                for m in range(rules["numbers_to_pick"] + 1)
            }
        assert sum(probabilities.values()) == 1, code
        payouts = {int(k): v for k, v in rules["fixed_payouts"].items()}
        for tier, (num, den) in rules["guaranteed_payouts"].items():
            payouts.setdefault(int(tier), at_price * num // den)
        if candidate and code in candidate_fixed_tiers:
            payouts = candidate_fixed_tiers[code]
        ordinary = sum(
            (probabilities[tier] * value for tier, value in payouts.items()), F(0)
        )
        return ordinary, probabilities[rules["jackpot_match"]]

    ordinary, pjackpot = expectation(price)
    candidate_price, candidate_base = proposals[code]
    candidate_ordinary, _ = expectation(candidate_price)
    revised_ordinary, _ = expectation(candidate_price, candidate=True)
    row = {
        "code": code,
        "jackpot_probability": str(pjackpot),
        "one_in": float(1 / pjackpot),
        "ordinary_expected_cas_without_sharing": float(ordinary),
        "current_base_reference_percent": float(
            100 * (ordinary + pjackpot * game["base_amount"]) / price
        )
        if code != "dual"
        else float(100 * ordinary / price),
        "current_pool_reference_percent": float(
            100 * (ordinary + pjackpot * game["jackpot_current"]) / price
        )
        if code != "dual"
        else float(100 * ordinary / price),
        "proposed_price_cas": candidate_price,
        "proposed_base_cas": candidate_base,
        "proposed_reference_percent_unchanged_tiers": float(
            100 * (candidate_ordinary + pjackpot * candidate_base) / candidate_price
        )
        if code != "dual"
        else float(100 * ordinary / candidate_price),
        "proposed_reference_percent_revised_tiers": float(
            100 * (revised_ordinary + pjackpot * candidate_base) / candidate_price
        )
        if code != "dual"
        else float(100 * revised_ordinary / candidate_price),
        "warning": (
            "Shared jackpots: no-sharing reference, NOT actual portfolio RTP. "
            "Bingo ordinary pools are shared too. Dual is fixed payout."
        ),
    }
    rows.append(row)

for game in snapshot["instant_games"]:
    assert sum(F(b["weight"], b["denominator"]) for b in game["bands"]) == 1
    expected = sum(F(b["prize"] * b["weight"], b["denominator"]) for b in game["bands"])
    proposed_price = 30_000 if game["code"] == "vault" else game["price"]
    rows.append(
        {
            "code": game["code"],
            "expected_cas": float(expected),
            "rtp_percent": float(100 * expected / game["price"]),
            "proposed_price_cas": proposed_price,
            "proposed_rtp_percent": float(100 * expected / proposed_price),
        }
    )

assert len(rows) == 14
assert next(x for x in rows if x["code"] == "vault")["expected_cas"] == 22_300
assert comb(15, 4) == 1365 and comb(28, 3) == 3276
assert 1365 * 22_000 == 30_030_000
assert 3276 * 6_666 == 21_837_816
(HERE / "metrics.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
for row in rows:
    print(json.dumps(row, ensure_ascii=True))
