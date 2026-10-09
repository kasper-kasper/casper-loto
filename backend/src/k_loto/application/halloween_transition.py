"""Compatibility names for the shared ledgered format transition service."""

from k_loto.application.lottery_transition import (
    LotteryFormatTransitionResult as HalloweenTransitionResult,
)
from k_loto.application.lottery_transition import (
    LotteryFormatTransitionService as HalloweenTransitionService,
)

__all__ = ["HalloweenTransitionResult", "HalloweenTransitionService"]
