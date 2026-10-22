"""Bounded declarative achievement conditions; no queries or executable catalog code."""

import hashlib
import json
from datetime import date, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

RARITIES = ("common", "uncommon", "rare", "epic", "legendary")
METRIC_EXTENSIONS: dict[str, bool] = {}


def register_metric(name: str, *, scoped: bool = False) -> None:
    """Called by trusted server adapters at startup, never by catalog JSON."""
    if name in BASE_METRICS or name in METRIC_EXTENSIONS or not name.isidentifier():
        raise ValueError("Metric name is invalid or already registered")
    METRIC_EXTENSIONS[name] = scoped


BASE_METRICS = frozenset(
    {
        "paid_tickets",
        "gift_tickets",
        "spent_tickets",
        "draw_participations",
        "lotteries_count",
        "winning_tickets",
        "prizes_count",
        "won_cas",
        "profit_cas",
        "max_ticket_win",
        "jackpots",
        "current_balance",
        "max_balance",
        "received_game_cas",
        "spent_cas",
        "active_days",
        "streak",
        "max_streak",
        "earned",
        "earned_category",
        "earned_period",
        "earned_set",
        "qualifying_wins",
        "result_count",
        "manual_tickets",
        "bulk_purchases",
        "rewarded_achievements",
        "winning_lotteries",
        "daily_winning_lotteries",
        "daily_play_types",
        "consecutive_winning_draws",
        "max_draw_winning_tickets",
        "daily_fast_winning_games",
    }
)
SCOPED_METRICS = frozenset(
    {
        "paid_tickets",
        "gift_tickets",
        "spent_tickets",
        "draw_participations",
        "winning_tickets",
        "prizes_count",
        "won_cas",
        "profit_cas",
        "max_ticket_win",
        "jackpots",
        "qualifying_wins",
        "result_count",
    }
)


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    metric: str
    op: Literal["gte", "gt", "eq", "lte", "lt"] = "gte"
    target: StrictInt = Field(ge=0, le=9_000_000_000_000_000_000)
    lottery: str | None = Field(default=None, pattern=r"^[a-z0-9-]{1,64}$")
    scope: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_.:-]{1,80}$")
    category: Literal["common", "uncommon", "rare", "epic", "legendary"] | None = None
    period_days: StrictInt | None = Field(default=None, ge=1, le=366)
    achievement_codes: list[str] | None = Field(
        default=None, min_length=1, max_length=32
    )
    min_prize: StrictInt | None = Field(default=None, ge=1)
    multiplier_numerator: StrictInt | None = Field(default=None, ge=1)
    multiplier_denominator: StrictInt = Field(default=1, ge=1)
    matches: StrictInt | None = Field(default=None, ge=0)
    matches_any: list[StrictInt] | None = Field(
        default=None, min_length=1, max_length=16
    )
    primary_matches: StrictInt | None = Field(default=None, ge=0)
    secondary_matches: StrictInt | None = Field(default=None, ge=0)
    bingo_row_move_lte: StrictInt | None = Field(default=None, ge=1, le=60)
    bingo_full_move_lte: StrictInt | None = Field(default=None, ge=1, le=60)
    natural_jackpot: bool | None = None
    payout_vs_price: Literal["eq", "gt"] | None = None
    prize_category: str | None = Field(default=None, pattern=r"^[a-z0-9_.+-]{1,64}$")

    @model_validator(mode="after")
    def supported(self) -> "Condition":
        if self.metric not in BASE_METRICS and self.metric not in METRIC_EXTENSIONS:
            raise ValueError("Unsupported metric; register a domain adapter first")
        if self.lottery and self.metric not in SCOPED_METRICS:
            raise ValueError("This metric cannot be scoped to a lottery")
        if self.scope and not METRIC_EXTENSIONS.get(self.metric):
            raise ValueError("Only a registered scoped extension accepts scope")
        if (self.category is not None) != (self.metric == "earned_category"):
            raise ValueError(
                "earned_category requires category, and only it accepts one"
            )
        if (self.period_days is not None) != (self.metric == "earned_period"):
            raise ValueError("earned_period requires period_days")
        if (self.achievement_codes is not None) != (self.metric == "earned_set"):
            raise ValueError("earned_set requires a fixed list of achievement codes")
        if self.achievement_codes is not None and (
            len(set(self.achievement_codes)) != len(self.achievement_codes)
            or any(not code or len(code) > 80 for code in self.achievement_codes)
            or self.target > len(self.achievement_codes)
        ):
            raise ValueError("Achievement set must be distinct and reachable")
        filters = (
            self.min_prize,
            self.multiplier_numerator,
            self.matches,
            self.matches_any,
            self.primary_matches,
            self.secondary_matches,
            self.bingo_row_move_lte,
            self.bingo_full_move_lte,
            self.natural_jackpot,
            self.prize_category,
            self.payout_vs_price,
        )
        if any(v is not None for v in filters) and self.metric not in {
            "qualifying_wins",
            "result_count",
        }:
            raise ValueError("Result filters require a result counter")
        if self.metric in {"qualifying_wins", "result_count"} and not any(
            v is not None for v in filters
        ):
            raise ValueError("A filtered counter requires at least one filter")
        if self.multiplier_denominator != 1 and self.multiplier_numerator is None:
            raise ValueError("Multiplier denominator requires numerator")
        if self.matches_any is not None and any(
            value < 0 for value in self.matches_any
        ):
            raise ValueError("Match codes must be nonnegative")
        return self

    @property
    def key(self) -> str:
        if self.achievement_codes is not None:
            encoded = json.dumps(sorted(self.achievement_codes)).encode()
            return "earned_set:" + hashlib.sha256(encoded).hexdigest()[:24]
        if self.metric in {"qualifying_wins", "result_count"}:
            data = self.model_dump(exclude={"op", "target"}, exclude_none=True)
            if self.matches_any is not None:
                data["matches_any"] = sorted(set(self.matches_any))
            digest = hashlib.sha256(
                json.dumps(data, sort_keys=True).encode()
            ).hexdigest()[:24]
            return f"{self.metric}:{digest}"
        return metric_key(
            self.metric, self.lottery or self.category or self.scope or ""
        )

    def accepts(self, value: int) -> bool:
        return {
            "gte": value >= self.target,
            "gt": value > self.target,
            "eq": value == self.target,
            "lte": value <= self.target,
            "lt": value < self.target,
        }[self.op]

    def matches_result(self, result: dict[str, Any]) -> bool:
        return (
            (not self.lottery or result["lottery"] == self.lottery)
            and (self.metric != "qualifying_wins" or result["prize"] > 0)
            and (self.min_prize is None or result["prize"] >= self.min_prize)
            and (
                self.payout_vs_price is None
                or (self.payout_vs_price == "eq" and result["prize"] == result["paid"])
                or (self.payout_vs_price == "gt" and result["prize"] > result["paid"])
            )
            and (self.matches is None or result["matches"] == self.matches)
            and (self.matches_any is None or result["matches"] in self.matches_any)
            and (
                self.primary_matches is None
                or result.get("primary_matches") == self.primary_matches
            )
            and (
                self.secondary_matches is None
                or result.get("secondary_matches") == self.secondary_matches
            )
            and (
                self.bingo_row_move_lte is None
                or (
                    result.get("first_row_move") is not None
                    and result["first_row_move"] <= self.bingo_row_move_lte
                )
            )
            and (
                self.bingo_full_move_lte is None
                or (
                    result.get("full_card_move") is not None
                    and result["full_card_move"] <= self.bingo_full_move_lte
                )
            )
            and (
                self.natural_jackpot is None
                or result["natural_jackpot"] == self.natural_jackpot
            )
            and (
                self.prize_category is None
                or self.prize_category in result["categories"]
            )
            and (
                self.multiplier_numerator is None
                or (
                    result["prize"] * self.multiplier_denominator
                    >= result["standard_price"] * self.multiplier_numerator
                )
            )
        )


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    mode: Literal["all", "any"] = "all"
    conditions: list[Condition] = Field(min_length=1, max_length=16)


class RewardSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    type: Literal[
        "cas", "ticket_entitlement", "cosmetic", "ticket", "ticket_pack", "case"
    ]
    amount: StrictInt | None = Field(default=None, ge=1, le=9_000_000_000_000_000_000)
    lottery: str | None = None
    item: str | None = None
    planned: bool = False

    @model_validator(mode="after")
    def complete(self) -> "RewardSpec":
        if self.planned != (self.type == "case"):
            raise ValueError("Only future cases are planned rewards")
        if self.type == "cas" and (self.amount is None or self.lottery or self.item):
            raise ValueError("CAS reward requires amount only")
        if self.type == "ticket_entitlement" and (
            not self.lottery or self.amount is None or self.item
        ):
            raise ValueError("Ticket entitlement requires lottery and count")
        if self.type in {"ticket", "ticket_pack"} and (
            self.lottery
            not in {
                "september",
                "grob",
                "pll",
                "khan",
                "pss",
                "weekly",
                "bingo",
                "flash",
                "shadow",
                "pulse",
            }
            or self.amount is None
            or not 1 <= self.amount <= (500 if self.type == "ticket_pack" else 1)
            or self.item
        ):
            raise ValueError("Gift requires a supported draw game and bounded quantity")
        if self.type == "case" and (
            self.amount is None
            or not 1 <= self.amount <= 200
            or self.lottery
            or self.item
        ):
            raise ValueError("Future case reward requires one to 200 ordinary cases")
        if self.type == "cosmetic" and (
            not self.item or self.amount is not None or self.lottery
        ):
            raise ValueError("Cosmetic reward requires item only")
        return self


def metric_key(metric: str, scope: str = "") -> str:
    return f"{metric}:{scope}" if scope else metric


def activity_progress(last: str | None, current: date, streak: int) -> tuple[int, int]:
    if last is not None and current <= date.fromisoformat(last):
        return 0, streak
    consecutive = last is not None and current - date.fromisoformat(last) == timedelta(
        days=1
    )
    return 1, streak + 1 if consecutive else 1
