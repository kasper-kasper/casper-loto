"""Independent New Year 2027 series, without a progressive jackpot."""

import json
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op

revision = "0067_new_year_2027"
down_revision = "0066_casper_mini"
branch_labels = None
depends_on = None

LOTTERY_ID = UUID("10000000-0000-0000-0000-000000001067")


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            INSERT INTO lotteries (
                id, code, name, kind, ruleset_code, numbers_to_pick,
                max_number, ticket_price, timezone, schedule,
                sales_cutoff_minutes, max_tickets_per_purchase,
                max_tickets_per_user_per_draw, is_active,
                next_draw_number, next_ticket_number, economy_epoch
            ) VALUES (
                :id, 'newyear2027', 'Новогоднее лото 2027', 'DAILY',
                'newyear_2027_3_12', 3, 12, 10000, 'Europe/Moscow',
                CAST(:schedule AS jsonb), 2, 101, 101, true, 1, 1,
                COALESCE((SELECT epoch FROM economy_control WHERE id=1), 1)
            )
        """),
        {
            "id": LOTTERY_ID,
            "schedule": json.dumps(
                {
                    "slots": ["21:15"],
                    "future_draw_count": 5,
                    "live_enabled": True,
                }
            ),
        },
    )
    # Zero compatibility accounts let the shared transactional engine retain
    # purchase, refund and recovery semantics. No money is issued or reserved.
    connection.execute(
        sa.text("""
            INSERT INTO jackpot_accounts
                (id, lottery_id, balance, base_amount, version)
            VALUES (:id, :lottery, 0, 0, 1)
        """),
        {"id": uuid4(), "lottery": LOTTERY_ID},
    )
    for table in ("distribution_funds", "lottery_reserves"):
        connection.execute(
            sa.text(f"""
                INSERT INTO {table} (id, lottery_id, balance, version)
                VALUES (:id, :lottery, 0, 1)
            """),
            {"id": uuid4(), "lottery": LOTTERY_ID},
        )


def downgrade() -> None:
    raise RuntimeError("Preserve New Year tickets, draws and ledger; migrate forward.")
