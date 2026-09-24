"""Add one-ticket/two-draw Casper Dual history and product entity."""

# ruff: noqa: E501  -- SQL statements are kept intact for migration review.

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0046_casper_dual"
down_revision: str | Sequence[str] | None = "0045_force_pss_casper_ball"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("second_draw_id", sa.Uuid(), nullable=True))
    op.add_column(
        "tickets", sa.Column("dual_night_matches", sa.Integer(), nullable=True)
    )
    op.add_column(
        "tickets", sa.Column("dual_dawn_matches", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        "fk_tickets_second_draw_id_draws",
        "tickets",
        "draws",
        ["second_draw_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_ticket_second_draw", "tickets", ["second_draw_id"])
    op.create_check_constraint(
        "ck_tickets_distinct_dual_draws",
        "tickets",
        "second_draw_id IS NULL OR second_draw_id <> draw_id",
    )
    op.create_check_constraint(
        "ck_tickets_dual_night_matches",
        "tickets",
        "dual_night_matches IS NULL OR dual_night_matches BETWEEN 0 AND 2",
    )
    op.create_check_constraint(
        "ck_tickets_dual_dawn_matches",
        "tickets",
        "dual_dawn_matches IS NULL OR dual_dawn_matches BETWEEN 0 AND 2",
    )
    connection = op.get_bind()
    lottery_id = str(uuid4())
    connection.execute(
        sa.text("""
        INSERT INTO lotteries (id, code, name, kind, ruleset_code, numbers_to_pick, max_number,
          ticket_price, timezone, schedule, sales_cutoff_minutes, max_tickets_per_purchase,
          max_tickets_per_user_per_draw, is_active, next_draw_number, next_ticket_number)
        VALUES (CAST(:id AS uuid), 'dual', 'Casper Dual', 'DAILY', 'casper_dual_2_12_2_12', 4, 24,
          20000, 'Europe/Moscow', CAST(:schedule AS jsonb), 2, 1000, 5000, true, 1, 1)
    """),
        {
            "id": lottery_id,
            "schedule": '{"slots":["00:30","07:30"],"future_draw_count":3}',
        },
    )
    fund_id = "4b415350-4552-4655-4e44-000000000001"
    fund_before = connection.execute(
        sa.text(
            "SELECT balance FROM kasper_fund_accounts WHERE id=CAST(:id AS uuid) FOR UPDATE"
        ),
        {"id": fund_id},
    ).scalar_one()
    if fund_before < 5_000_000:
        raise RuntimeError("Kasper Fund cannot fund the initial Casper Dual jackpot.")
    operation_id = str(uuid4())
    connection.execute(
        sa.text(
            "UPDATE kasper_fund_accounts SET balance=balance-5000000, version=version+1 WHERE id=CAST(:id AS uuid)"
        ),
        {"id": fund_id},
    )
    connection.execute(
        sa.text("""
        INSERT INTO ledger_transactions (id, operation_id, idempotency_key, account_kind, account_id,
          type, amount, balance_before, balance_after, lottery_id, metadata)
        VALUES (CAST(:id AS uuid), CAST(:operation AS uuid), 'migration:0046:dual:fund', 'KASPER_FUND', CAST(:fund AS uuid),
          'SYSTEM_ADJUSTMENT', -5000000, :before, :after, CAST(:lottery AS uuid), CAST(:metadata AS jsonb))
    """),
        {
            "id": str(uuid4()),
            "operation": operation_id,
            "fund": fund_id,
            "before": fund_before,
            "after": fund_before - 5_000_000,
            "lottery": lottery_id,
            "metadata": '{"reason":"Initial Casper Dual jackpot"}',
        },
    )
    for table in ("jackpot_accounts", "distribution_funds", "lottery_reserves"):
        if table == "jackpot_accounts":
            account_id = str(uuid4())
            connection.execute(
                sa.text(
                    "INSERT INTO jackpot_accounts (id, lottery_id, balance, base_amount, version) VALUES (CAST(:id AS uuid), CAST(:lottery_id AS uuid), 5000000, 5000000, 1)"
                ),
                {"id": account_id, "lottery_id": lottery_id},
            )
            connection.execute(
                sa.text("""
                INSERT INTO ledger_transactions (id, operation_id, idempotency_key, account_kind, account_id,
                  type, amount, balance_before, balance_after, lottery_id, metadata)
                VALUES (CAST(:id AS uuid), CAST(:operation AS uuid), 'migration:0046:dual:jackpot', 'JACKPOT', CAST(:account AS uuid),
                  'SYSTEM_ADJUSTMENT', 5000000, 0, 5000000, CAST(:lottery AS uuid), CAST(:metadata AS jsonb))
            """),
                {
                    "id": str(uuid4()),
                    "operation": operation_id,
                    "account": account_id,
                    "lottery": lottery_id,
                    "metadata": '{"reason":"Initial Casper Dual jackpot"}',
                },
            )
        else:
            connection.execute(
                sa.text(
                    f"INSERT INTO {table} (id, lottery_id, balance, version) VALUES (CAST(:id AS uuid), CAST(:lottery_id AS uuid), 0, 1)"
                ),
                {"id": str(uuid4()), "lottery_id": lottery_id},
            )


def downgrade() -> None:
    raise RuntimeError("Casper Dual history cannot be removed safely.")
