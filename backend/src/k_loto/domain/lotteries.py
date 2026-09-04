"""Stable public lottery identities and draw presentation metadata."""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from k_loto.domain.enums import LotteryKind


@dataclass(frozen=True, slots=True)
class LotteryDefinition:
    code: str
    name: str
    kind: LotteryKind
    draw_time: str


LOTTERY_DEFINITIONS = (
    LotteryDefinition("weekly", "Kasper Grand", LotteryKind.WEEKLY, "20:00"),
    LotteryDefinition("pll", "ПЛЛ-лото", LotteryKind.DAILY, "02:22 / 13:45"),
    LotteryDefinition("pss", "ПСС-Лото", LotteryKind.DAILY, "12:00 / 20:30"),
    LotteryDefinition("khan", "ХАН-Лото", LotteryKind.DAILY, "09:00 / 18:00"),
    LotteryDefinition("september", "3 СЕНТЯБРЯ", LotteryKind.DAILY, "03:33 / 15:33"),
    LotteryDefinition("grob", "ГРОБ", LotteryKind.DAILY, "06:06 / 23:06"),
    LotteryDefinition("flash", "FLASH", LotteryKind.DAILY, "каждые 9 минут"),
    LotteryDefinition("shadow", "SHADOW", LotteryKind.DAILY, "каждые 9 минут"),
    LotteryDefinition("pulse", "PULSE", LotteryKind.DAILY, "каждые 9 минут"),
)

PLAYABLE_LOTTERY_CODES = frozenset(item.code for item in LOTTERY_DEFINITIONS)
DAILY_LOTTERY_CODES = frozenset(
    item.code for item in LOTTERY_DEFINITIONS if item.kind == LotteryKind.DAILY
)
FAST_LOTTERY_CODES = frozenset({"flash", "shadow", "pulse"})


def is_fast_lottery(code: str) -> bool:
    """Return whether a stable lottery identity belongs to the Fast section."""
    return code in FAST_LOTTERY_CODES


MOSCOW = ZoneInfo("Europe/Moscow")
DAILY_SLOT_NAMES = {
    (2, 22): "ПЛЛ-лото",
    (12, 0): "ПСС-лото",
    (18, 0): "ХАН-лото",
}
DAILY_SLOT_CODES = {
    (2, 22): "pll",
    (12, 0): "pss",
    (18, 0): "khan",
}


def daily_draw_name(scheduled_at: datetime) -> str:
    """Return the immutable public label for a Moscow daily draw slot."""
    local = scheduled_at.astimezone(MOSCOW)
    return DAILY_SLOT_NAMES.get((local.hour, local.minute), "Ежедневная лотерея")


def draw_display_name(
    lottery_code: str, lottery_name: str, scheduled_at: datetime
) -> str:
    """Present unified Daily draws by their slot name and legacy draws as stored."""
    if lottery_code == "daily":
        return daily_draw_name(scheduled_at)
    return lottery_name


def draw_display_code(lottery_code: str, scheduled_at: datetime) -> str:
    """Map a preserved shared-Daily draw to its public independent identity."""
    if lottery_code != "daily":
        return lottery_code
    local = scheduled_at.astimezone(MOSCOW)
    return DAILY_SLOT_CODES.get((local.hour, local.minute), lottery_code)
