"""Finish the PSS transition after the interrupted 0043 migration."""

import json
from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "0044_finish_pss_casper_ball"
down_revision: str | Sequence[str] | None = "0043_pss_casper_ball"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RULESET = "casper_ball_5_36_1_8"
TARGET_JACKPOT = 50_000_000


def _ledger(
    connection: sa.Connection,
    *,
    kind: str,
    account_id: object,
    amount: int,
    before: int,
    lottery_id: object,
    transaction_type: str,
    key: str,
    user_id: object | None = None,
    details: dict[str, object] | None = None,
) -> None:
    if amount == 0:
        return
    connection.execute(
        sa.text(
            """
            INSERT INTO ledger_transactions (
                id, operation_id, idempotency_key, account_kind, account_id,
                type, amount, balance_before, balance_after, user_id,
                lottery_id, created_at, metadata
            ) VALUES (
                :id, :operation_id, :key, :kind, :account_id,
                :type, :amount, :before, :after, :user_id,
                :lottery_id, now(), CAST(:metadata AS jsonb)
            )
            """
        ),
        {
            "id": uuid4(),
            "operation_id": uuid4(),
            "key": key,
            "kind": kind,
            "account_id": account_id,
            "amount": amount,
            "before": before,
            "after": before + amount,
            "user_id": user_id,
            "lottery_id": lottery_id,
            "type": transaction_type,
            "metadata": json.dumps(details or {}, ensure_ascii=False),
        },
    )


def upgrade() -> None:
    connection = op.get_bind()
    lottery = (
        connection.execute(
            sa.text(
                """
                SELECT l.id, l.name, l.ruleset_code, l.ticket_price,
                       j.id AS jackpot_id, j.balance AS jackpot_balance
                FROM lotteries l
                JOIN jackpot_accounts j ON j.lottery_id=l.id
                WHERE l.code='pss'
                FOR UPDATE OF l, j
                """
            )
        )
        .mappings()
        .one_or_none()
    )
    if lottery is None:
        raise RuntimeError("PSS lottery is missing; refusing to finish transition.")

    lottery_id = lottery["id"]
    refunds = (
        connection.execute(
            sa.text(
                """
                SELECT t.user_id, SUM(t.purchase_price)::bigint AS amount,
                       COUNT(*)::integer AS ticket_count,
                       array_agg(t.id ORDER BY t.public_number) AS ticket_ids
                FROM tickets t
                JOIN draws d ON d.id=t.draw_id
                WHERE t.lottery_id=:lottery_id AND t.status='PURCHASED'
                  AND d.status='SCHEDULED'
                GROUP BY t.user_id
                """
            ),
            {"lottery_id": lottery_id},
        )
        .mappings()
        .all()
    )
    total_refund = sum(int(row["amount"]) for row in refunds)
    jackpot_before = int(lottery["jackpot_balance"])
    after_refund = jackpot_before - total_refund
    if after_refund < 0:
        raise RuntimeError("PSS jackpot cannot cover the pending ticket refunds.")

    connection.execute(
        sa.text(
            """
            WITH refunded AS (
                SELECT t.draw_id, COUNT(*)::integer AS ticket_count,
                       SUM(t.purchase_price)::bigint AS total_sales
                FROM tickets t JOIN draws d ON d.id=t.draw_id
                WHERE t.lottery_id=:lottery_id AND t.status='PURCHASED'
                  AND d.status='SCHEDULED'
                GROUP BY t.draw_id
            )
            UPDATE draws d SET ticket_count=d.ticket_count-refunded.ticket_count,
                total_sales=d.total_sales-refunded.total_sales
            FROM refunded WHERE d.id=refunded.draw_id
            """
        ),
        {"lottery_id": lottery_id},
    )
    for row in refunds:
        before = int(
            connection.execute(
                sa.text(
                    "SELECT amount FROM balances WHERE user_id=:user_id FOR UPDATE"
                ),
                {"user_id": row["user_id"]},
            ).scalar_one()
        )
        amount = int(row["amount"])
        connection.execute(
            sa.text(
                "UPDATE balances SET amount=:amount, version=version+1, "
                "updated_at=now() "
                "WHERE user_id=:user_id"
            ),
            {"amount": before + amount, "user_id": row["user_id"]},
        )
        _ledger(
            connection,
            kind="USER_BALANCE",
            account_id=row["user_id"],
            user_id=row["user_id"],
            amount=amount,
            before=before,
            lottery_id=lottery_id,
            transaction_type="TICKET_REFUND",
            key=f"migration:0044:pss-refund:user:{row['user_id']}",
            details={
                "reason": "Finish owner-approved PSS format transition",
                "ticket_count": int(row["ticket_count"]),
                "ticket_ids": [str(value) for value in row["ticket_ids"]],
            },
        )

    if total_refund:
        _ledger(
            connection,
            kind="JACKPOT",
            account_id=lottery["jackpot_id"],
            amount=-total_refund,
            before=jackpot_before,
            lottery_id=lottery_id,
            transaction_type="TICKET_REFUND",
            key="migration:0044:pss-refund:jackpot",
            details={"refunded_ticket_total": total_refund},
        )
    _ledger(
        connection,
        kind="JACKPOT",
        account_id=lottery["jackpot_id"],
        amount=TARGET_JACKPOT - after_refund,
        before=after_refund,
        lottery_id=lottery_id,
        transaction_type="SYSTEM_ADJUSTMENT",
        key="migration:0044:pss-jackpot-target",
        details={"reason": "Finish Casper Ball opening jackpot"},
    )
    connection.execute(
        sa.text(
            "UPDATE jackpot_accounts SET balance=:balance, base_amount=:balance, "
            "version=version+1, updated_at=now() WHERE id=:id"
        ),
        {"balance": TARGET_JACKPOT, "id": lottery["jackpot_id"]},
    )
    connection.execute(
        sa.text(
            "UPDATE tickets SET status='REFUNDED', settled_at=now() "
            "WHERE lottery_id=:lottery_id AND status='PURCHASED' "
            "AND draw_id IN (SELECT id FROM draws WHERE status='SCHEDULED')"
        ),
        {"lottery_id": lottery_id},
    )
    connection.execute(
        sa.text("DELETE FROM favorite_combinations WHERE lottery_id=:lottery_id"),
        {"lottery_id": lottery_id},
    )
    connection.execute(
        sa.text(
            "UPDATE lotteries SET name='Casper Ball', ruleset_code=:ruleset, "
            "numbers_to_pick=6, max_number=44, updated_at=now() WHERE id=:id"
        ),
        {"ruleset": RULESET, "id": lottery_id},
    )
    connection.execute(
        sa.text(
            """
            UPDATE draws SET configuration_snapshot=jsonb_build_object(
                'ruleset_code', CAST(:ruleset AS text),
                'ticket_price', CAST(:ticket_price AS bigint),
                'numbers_to_pick', 6, 'max_number', 44,
                'base_jackpot', CAST(:base_jackpot AS bigint)
            ), updated_at=now()
            WHERE lottery_id=:lottery_id AND status='SCHEDULED'
            """
        ),
        {
            "ruleset": RULESET,
            "ticket_price": lottery["ticket_price"],
            "base_jackpot": TARGET_JACKPOT,
            "lottery_id": lottery_id,
        },
    )


def downgrade() -> None:
    raise RuntimeError("PSS transition corrections are irreversible.")
