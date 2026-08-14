"""Stable domain enum values persisted by the database."""

from enum import StrEnum


class LotteryKind(StrEnum):
    WEEKLY = "WEEKLY"
    DAILY = "DAILY"


class DrawStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    CLOSED = "CLOSED"
    DRAWING = "DRAWING"
    SETTLING = "SETTLING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TicketStatus(StrEnum):
    PURCHASED = "PURCHASED"
    SETTLED = "SETTLED"


class LedgerAccountKind(StrEnum):
    USER_BALANCE = "USER_BALANCE"
    JACKPOT = "JACKPOT"
    DISTRIBUTION_FUND = "DISTRIBUTION_FUND"
    LOTTERY_RESERVE = "LOTTERY_RESERVE"


class TransactionType(StrEnum):
    ADMIN_BALANCE_ADJUSTMENT = "ADMIN_BALANCE_ADJUSTMENT"
    TICKET_PURCHASE = "TICKET_PURCHASE"
    PRIZE_PAYOUT = "PRIZE_PAYOUT"
    JACKPOT_PAYOUT = "JACKPOT_PAYOUT"
    RESERVE_ADJUSTMENT = "RESERVE_ADJUSTMENT"
    SYSTEM_ADJUSTMENT = "SYSTEM_ADJUSTMENT"


class AuditAction(StrEnum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    ADJUST = "ADJUST"
