"""Add permanent Casper Mini with independent accounts and number sequences."""

import json
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op

revision = "0066_casper_mini"
down_revision = "0065_achievement_launch"
branch_labels = None
depends_on = None

LOTTERY_ID = UUID("10000000-0000-0000-0000-000000001066")
JACKPOT_ID = UUID("10000000-0000-0000-0000-000000001166")
SCHEDULE = {
    "slots": ["10:30", "19:15"],
    "future_draw_count": 5,
    "live_enabled": True,
}

# Keep actual wallet balances current, but exclude Mini spending and game
# receipts from achievement counters until the owner enables this product.
# ruff: noqa: E501 -- frozen SQL trigger definition.
WALLET_CAPTURE = """
CREATE OR REPLACE FUNCTION capture_achievement_wallet() RETURNS trigger AS $$
DECLARE batch text; started timestamptz;
BEGIN
 SELECT started_at INTO started FROM achievement_runtime WHERE id=1 AND enabled;
 IF started IS NULL THEN RETURN NULL; END IF;
 batch := achievement_batch_id();
 INSERT INTO achievement_events(event_key,kind,user_id,payload)
 SELECT 'wallet:'||batch||':'||l.user_id,'wallet',l.user_id,
 jsonb_build_object('delta',sum(amount),'maximum',max(greatest(balance_before,balance_after)),
 'spent',coalesce(-sum(amount) FILTER(WHERE coalesce(g.code,'')<>'mini' AND (type='TICKET_PURCHASE' OR (type='TICKET_REFUND' AND t.purchased_at>=started))),0),
 'game',coalesce(sum(amount) FILTER(WHERE coalesce(g.code,'')<>'mini' AND amount>0 AND type IN ('PRIZE_PAYOUT','JACKPOT_PAYOUT')),0))
 FROM achievement_new_ledger l LEFT JOIN tickets t ON t.id=l.ticket_id
 LEFT JOIN lotteries g ON g.id=l.lottery_id
 WHERE account_kind='USER_BALANCE' AND l.user_id IS NOT NULL GROUP BY l.user_id
 ON CONFLICT(event_key) DO UPDATE SET payload=jsonb_build_object(
 'delta',(achievement_events.payload->>'delta')::bigint+(EXCLUDED.payload->>'delta')::bigint,
 'maximum',greatest((achievement_events.payload->>'maximum')::bigint,(EXCLUDED.payload->>'maximum')::bigint),
 'spent',(achievement_events.payload->>'spent')::bigint+(EXCLUDED.payload->>'spent')::bigint,
 'game',(achievement_events.payload->>'game')::bigint+(EXCLUDED.payload->>'game')::bigint);
 RETURN NULL;
END; $$ LANGUAGE plpgsql;
"""


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
                :id, 'mini', 'Casper Mini', 'DAILY', 'casper_mini_6_30', 6, 30,
                10000, 'Europe/Moscow', CAST(:schedule AS jsonb),
                2, 100, 500, true, 1, 1,
                COALESCE((SELECT epoch FROM economy_control WHERE id=1), 1)
            )
        """),
        {"id": LOTTERY_ID, "schedule": json.dumps(SCHEDULE)},
    )
    connection.execute(
        sa.text("""
            INSERT INTO jackpot_accounts
                (id, lottery_id, balance, base_amount, version)
            VALUES (:id, :lottery_id, 20000000, 20000000, 1)
        """),
        {"id": JACKPOT_ID, "lottery_id": LOTTERY_ID},
    )
    for table in ("distribution_funds", "lottery_reserves"):
        connection.execute(
            sa.text(f"""
                INSERT INTO {table} (id, lottery_id, balance, version)
                VALUES (:id, :lottery_id, 0, 1)
            """),
            {"id": uuid4(), "lottery_id": LOTTERY_ID},
        )
    connection.execute(
        sa.text("""
            INSERT INTO ledger_transactions (
                id, operation_id, idempotency_key, account_kind, account_id,
                type, amount, balance_before, balance_after, lottery_id, metadata
            ) VALUES (
                :id, :operation, 'migration:0066:mini:jackpot', 'JACKPOT',
                :account, 'SYSTEM_ADJUSTMENT', 20000000, 0, 20000000,
                :lottery, CAST(:metadata AS jsonb)
            )
        """),
        {
            "id": uuid4(),
            "operation": uuid4(),
            "account": JACKPOT_ID,
            "lottery": LOTTERY_ID,
            "metadata": json.dumps({"reason": "Casper Mini initial jackpot"}),
        },
    )
    op.execute(WALLET_CAPTURE)


def downgrade() -> None:
    raise RuntimeError("Preserve Casper Mini history and ledger; migrate forward.")
