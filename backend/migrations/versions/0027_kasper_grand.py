"""Convert the future Weekly draw to Kasper Grand and refund old entries.

Revision ID: 0027_kasper_grand
Revises: 0026_fast_live
Create Date: 2026-09-04
"""

import json
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0027_kasper_grand"
down_revision: str | Sequence[str] | None = "0026_fast_live"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ticket_status", "tickets", type_="check")
    op.create_check_constraint(
        "ticket_status",
        "tickets",
        "status IN ('PURCHASED', 'SETTLED', 'REFUNDED')",
    )
    op.drop_constraint("transaction_type", "ledger_transactions", type_="check")
    op.create_check_constraint(
        "transaction_type",
        "ledger_transactions",
        "type IN ('ADMIN_BALANCE_ADJUSTMENT', 'TICKET_PURCHASE', "
        "'TICKET_REFUND', 'PRIZE_PAYOUT', 'JACKPOT_PAYOUT', "
        "'RESERVE_ADJUSTMENT', 'SYSTEM_ADJUSTMENT')",
    )

    connection = op.get_bind()
    lottery = (
        connection.execute(
            sa.text(
                """
            SELECT l.id, l.ticket_price, j.id AS jackpot_id,
                   j.balance AS jackpot_balance, j.base_amount
            FROM lotteries AS l
            JOIN jackpot_accounts AS j ON j.lottery_id = l.id
            WHERE l.code = 'weekly'
            FOR UPDATE OF l, j
            """
            )
        )
        .mappings()
        .one_or_none()
    )
    if lottery is None:
        return
    lottery_id = lottery["id"]

    refunds = (
        connection.execute(
            sa.text(
                """
                SELECT t.user_id, SUM(t.purchase_price)::bigint AS amount,
                       COUNT(*)::integer AS ticket_count,
                       array_agg(t.id ORDER BY t.public_number) AS ticket_ids
                FROM tickets AS t
                JOIN draws AS d ON d.id = t.draw_id
                WHERE t.lottery_id = :lottery_id
                  AND t.status = 'PURCHASED'
                  AND d.status = 'SCHEDULED'
                GROUP BY t.user_id
                ORDER BY t.user_id
                """
            ),
            {"lottery_id": lottery_id},
        )
        .mappings()
        .all()
    )
    total_refund = sum(int(row["amount"]) for row in refunds)
    if total_refund > int(lottery["jackpot_balance"]):
        raise RuntimeError("Weekly jackpot cannot cover the required ticket refunds.")

    connection.execute(
        sa.text(
            """
            WITH refunded AS (
                SELECT t.draw_id, COUNT(*)::integer AS ticket_count,
                       SUM(t.purchase_price)::bigint AS total_sales
                FROM tickets AS t
                JOIN draws AS d ON d.id = t.draw_id
                WHERE t.lottery_id = :lottery_id
                  AND t.status = 'PURCHASED'
                  AND d.status = 'SCHEDULED'
                GROUP BY t.draw_id
            )
            UPDATE draws AS d
            SET ticket_count = d.ticket_count - refunded.ticket_count,
                total_sales = d.total_sales - refunded.total_sales
            FROM refunded
            WHERE d.id = refunded.draw_id
            """
        ),
        {"lottery_id": lottery_id},
    )

    for row in refunds:
        balance = connection.execute(
            sa.text("SELECT amount FROM balances WHERE user_id = :user_id FOR UPDATE"),
            {"user_id": row["user_id"]},
        ).scalar_one()
        after = int(balance) + int(row["amount"])
        operation_id = uuid4()
        idempotency_key = f"migration:0027:weekly-refund:user:{row['user_id']}"
        connection.execute(
            sa.text(
                """
                UPDATE balances
                SET amount = :after, version = version + 1, updated_at = now()
                WHERE user_id = :user_id
                """
            ),
            {"after": after, "user_id": row["user_id"]},
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO ledger_transactions (
                    id, operation_id, idempotency_key, account_kind, account_id,
                    type, amount, balance_before, balance_after, user_id,
                    lottery_id, created_at, metadata
                ) VALUES (
                    :id, :operation_id, :idempotency_key, 'USER_BALANCE', :user_id,
                    'TICKET_REFUND', :amount, :before, :after, :user_id,
                    :lottery_id, now(), CAST(:metadata AS jsonb)
                )
                """
            ),
            {
                "id": uuid4(),
                "operation_id": operation_id,
                "idempotency_key": idempotency_key,
                "amount": int(row["amount"]),
                "before": int(balance),
                "after": after,
                "user_id": row["user_id"],
                "lottery_id": lottery_id,
                "metadata": json.dumps(
                    {
                        "reason": "Kasper Grand format transition",
                        "ticket_count": int(row["ticket_count"]),
                        "ticket_ids": [str(value) for value in row["ticket_ids"]],
                    }
                ),
            },
        )

    if total_refund:
        jackpot_after = int(lottery["jackpot_balance"]) - total_refund
        connection.execute(
            sa.text(
                """
                UPDATE jackpot_accounts
                SET balance = :after, version = version + 1, updated_at = now()
                WHERE id = :jackpot_id
                """
            ),
            {"after": jackpot_after, "jackpot_id": lottery["jackpot_id"]},
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO ledger_transactions (
                    id, operation_id, idempotency_key, account_kind, account_id,
                    type, amount, balance_before, balance_after, lottery_id,
                    created_at, metadata
                ) VALUES (
                    :id, :operation_id, 'migration:0027:weekly-refund:jackpot',
                    'JACKPOT', :jackpot_id, 'TICKET_REFUND', :amount, :before,
                    :after, :lottery_id, now(), CAST(:metadata AS jsonb)
                )
                """
            ),
            {
                "id": uuid4(),
                "operation_id": uuid4(),
                "jackpot_id": lottery["jackpot_id"],
                "amount": -total_refund,
                "before": int(lottery["jackpot_balance"]),
                "after": jackpot_after,
                "lottery_id": lottery_id,
                "metadata": json.dumps(
                    {
                        "reason": "Kasper Grand format transition",
                        "refunded_ticket_total": total_refund,
                    }
                ),
            },
        )

    connection.execute(
        sa.text(
            """
            UPDATE tickets AS t
            SET status = 'REFUNDED', settled_at = now()
            FROM draws AS d
            WHERE t.draw_id = d.id
              AND t.lottery_id = :lottery_id
              AND t.status = 'PURCHASED'
              AND d.status = 'SCHEDULED'
            """
        ),
        {"lottery_id": lottery_id},
    )
    connection.execute(
        sa.text("DELETE FROM favorite_combinations WHERE lottery_id = :lottery_id"),
        {"lottery_id": lottery_id},
    )
    connection.execute(
        sa.text(
            """
            UPDATE lotteries
            SET name = 'Kasper Grand', ruleset_code = 'weekly_grand_5_35_2_5',
                numbers_to_pick = 7, max_number = 40, updated_at = now()
            WHERE id = :lottery_id
            """
        ),
        {"lottery_id": lottery_id},
    )
    connection.execute(
        sa.text(
            """
            UPDATE draws
            SET configuration_snapshot = jsonb_build_object(
                    'ruleset_code', 'weekly_grand_5_35_2_5',
                    'ticket_price', :ticket_price,
                    'numbers_to_pick', 7,
                    'max_number', 40,
                    'base_jackpot', :base_jackpot
                ),
                updated_at = now()
            WHERE lottery_id = :lottery_id AND status = 'SCHEDULED'
            """
        ),
        {
            "ticket_price": lottery["ticket_price"],
            "base_jackpot": lottery["base_amount"],
            "lottery_id": lottery_id,
        },
    )


def downgrade() -> None:
    raise RuntimeError(
        "Kasper Grand migration contains immutable ledger refunds and is irreversible."
    )
