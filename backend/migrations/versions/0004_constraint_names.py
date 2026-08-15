"""Align database check-constraint names with SQLAlchemy metadata.

Revision ID: 0004_constraint_names
Revises: 0003_web_accounts
Create Date: 2026-08-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_constraint_names"
down_revision: str | Sequence[str] | None = "0003_web_accounts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CONSTRAINT_RENAMES = (
    (
        "balances",
        "ck_balances_ck_balances_amount_nonnegative",
        "ck_balances_amount_nonnegative",
    ),
    (
        "distribution_funds",
        "ck_distribution_funds_ck_distribution_funds_balance_nonnegative",
        "ck_distribution_funds_balance_nonnegative",
    ),
    (
        "draws",
        "ck_draws_ck_draws_public_number_positive",
        "ck_draws_public_number_positive",
    ),
    (
        "draws",
        "ck_draws_ck_draws_sales_close_before_draw",
        "ck_draws_sales_close_before_draw",
    ),
    (
        "draws",
        "ck_draws_ck_draws_ticket_count_nonnegative",
        "ck_draws_ticket_count_nonnegative",
    ),
    (
        "draws",
        "ck_draws_ck_draws_total_payout_nonnegative",
        "ck_draws_total_payout_nonnegative",
    ),
    (
        "draws",
        "ck_draws_ck_draws_total_sales_nonnegative",
        "ck_draws_total_sales_nonnegative",
    ),
    (
        "jackpot_accounts",
        "ck_jackpot_accounts_ck_jackpot_accounts_balance_nonnegative",
        "ck_jackpot_accounts_balance_nonnegative",
    ),
    (
        "jackpot_accounts",
        "ck_jackpot_accounts_ck_jackpot_accounts_base_amount_nonnegative",
        "ck_jackpot_accounts_base_amount_nonnegative",
    ),
    (
        "ledger_transactions",
        "ck_ledger_transactions_ck_ledger_transactions_amount_nonzero",
        "ck_ledger_transactions_amount_nonzero",
    ),
    (
        "ledger_transactions",
        "ck_ledger_transactions_ck_ledger_transactions_balance_a_15f8",
        "ck_ledger_transactions_balance_after_nonnegative",
    ),
    (
        "ledger_transactions",
        "ck_ledger_transactions_ck_ledger_transactions_balance_b_d8c9",
        "ck_ledger_transactions_balance_before_nonnegative",
    ),
    (
        "ledger_transactions",
        "ck_ledger_transactions_ck_ledger_transactions_balance_equation",
        "ck_ledger_transactions_balance_equation",
    ),
    (
        "lotteries",
        "ck_lotteries_ck_lotteries_max_number_valid",
        "ck_lotteries_max_number_valid",
    ),
    (
        "lotteries",
        "ck_lotteries_ck_lotteries_next_draw_number_positive",
        "ck_lotteries_next_draw_number_positive",
    ),
    (
        "lotteries",
        "ck_lotteries_ck_lotteries_next_ticket_number_positive",
        "ck_lotteries_next_ticket_number_positive",
    ),
    (
        "lotteries",
        "ck_lotteries_ck_lotteries_numbers_to_pick_positive",
        "ck_lotteries_numbers_to_pick_positive",
    ),
    (
        "lotteries",
        "ck_lotteries_ck_lotteries_ticket_price_positive",
        "ck_lotteries_ticket_price_positive",
    ),
    (
        "lottery_reserves",
        "ck_lottery_reserves_ck_lottery_reserves_balance_nonnegative",
        "ck_lottery_reserves_balance_nonnegative",
    ),
    (
        "notification_outbox",
        "ck_notification_outbox_ck_notification_outbox_attempts__8192",
        "ck_notification_outbox_attempts_nonnegative",
    ),
    (
        "tickets",
        "ck_tickets_ck_tickets_matches_nonnegative",
        "ck_tickets_matches_nonnegative",
    ),
    (
        "tickets",
        "ck_tickets_ck_tickets_prize_amount_nonnegative",
        "ck_tickets_prize_amount_nonnegative",
    ),
    (
        "tickets",
        "ck_tickets_ck_tickets_public_number_positive",
        "ck_tickets_public_number_positive",
    ),
    (
        "tickets",
        "ck_tickets_ck_tickets_purchase_price_positive",
        "ck_tickets_purchase_price_positive",
    ),
    (
        "web_accounts",
        "ck_web_accounts_ck_web_accounts_username_min_length",
        "ck_web_accounts_username_min_length",
    ),
)


def _rename(table: str, old_name: str, new_name: str) -> None:
    op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"')


def upgrade() -> None:
    for table, old_name, new_name in CONSTRAINT_RENAMES:
        _rename(table, old_name, new_name)


def downgrade() -> None:
    for table, old_name, new_name in reversed(CONSTRAINT_RENAMES):
        _rename(table, new_name, old_name)
