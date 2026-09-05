"""Shared read-only separation of ordinary lotteries and frequent Fast rounds."""

from typing import Literal

from sqlalchemy import true
from sqlalchemy.sql.elements import ColumnElement

from k_loto.domain.lotteries import FAST_LOTTERY_CODES
from k_loto.infrastructure.database.models import Lottery

LotteryScope = Literal["all", "standard", "fast"]


def lottery_scope(scope: LotteryScope) -> ColumnElement[bool]:
    if scope == "fast":
        return Lottery.code.in_(FAST_LOTTERY_CODES)
    if scope == "standard":
        return Lottery.code.not_in(FAST_LOTTERY_CODES)
    return true()
