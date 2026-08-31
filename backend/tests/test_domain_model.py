"""Milestone 1 domain model invariants."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import BigInteger, UniqueConstraint

from k_loto.domain.draw_state import ensure_draw_transition
from k_loto.domain.enums import DrawStatus
from k_loto.domain.errors import InvalidStateTransition
from k_loto.domain.lotteries import draw_display_code
from k_loto.infrastructure.database.base import Base


def test_all_required_domain_tables_are_registered() -> None:
    assert {
        "users",
        "lotteries",
        "draws",
        "tickets",
        "balances",
        "ledger_transactions",
        "jackpot_accounts",
        "distribution_funds",
        "lottery_reserves",
        "admin_audit_log",
        "notification_outbox",
        "web_accounts",
    }.issubset(Base.metadata.tables)


def test_draw_and_ticket_numbers_are_unique_per_lottery() -> None:
    draw_constraints = Base.metadata.tables["draws"].constraints
    ticket_constraints = Base.metadata.tables["tickets"].constraints

    assert any(
        isinstance(item, UniqueConstraint) and item.name == "uq_draw_lottery_number"
        for item in draw_constraints
    )
    assert any(
        isinstance(item, UniqueConstraint) and item.name == "uq_ticket_lottery_number"
        for item in ticket_constraints
    )


def test_all_cas_columns_use_big_integer() -> None:
    money_columns = {
        "lotteries": ("ticket_price",),
        "draws": ("total_sales", "total_payout"),
        "tickets": ("purchase_price", "prize_amount"),
        "balances": ("amount",),
        "jackpot_accounts": ("balance", "base_amount"),
        "distribution_funds": ("balance",),
        "lottery_reserves": ("balance",),
        "ledger_transactions": ("amount", "balance_before", "balance_after"),
    }

    for table_name, column_names in money_columns.items():
        table = Base.metadata.tables[table_name]
        for column_name in column_names:
            assert isinstance(table.c[column_name].type, BigInteger)


def test_completed_draw_is_terminal_state() -> None:
    with pytest.raises(InvalidStateTransition):
        ensure_draw_transition(DrawStatus.COMPLETED, DrawStatus.DRAWING)


def test_recovery_can_retry_failed_draw() -> None:
    ensure_draw_transition(DrawStatus.FAILED, DrawStatus.DRAWING)


def test_shared_daily_draw_keeps_its_public_slot_identity() -> None:
    assert (
        draw_display_code("daily", datetime(2026, 8, 31, 23, 22, tzinfo=UTC)) == "pll"
    )
    assert draw_display_code("daily", datetime(2026, 9, 1, 9, 0, tzinfo=UTC)) == "pss"
