"""Configure the named K-Loto lottery lineup.

Revision ID: 0006_lottery_lineup
Revises: 0005_telegram_web_login
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_lottery_lineup"
down_revision: str | Sequence[str] | None = "0005_telegram_web_login"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


LOTTERIES = (
    ("10000000-0000-0000-0000-000000000012", "pss", "ПСС-лото", "12:00"),
    ("10000000-0000-0000-0000-000000000018", "khan", "ХАН-лото", "18:00"),
    ("10000000-0000-0000-0000-000000000222", "pll", "ПЛЛ-лото", "02:22"),
)


def upgrade() -> None:
    op.execute("UPDATE lotteries SET name = 'ЛСД-лото' WHERE code = 'weekly'")
    # The former combined Daily entity remains as a read-only historical parent.
    # Its completed draws and tickets are deliberately not reassigned.
    op.execute(
        "UPDATE lotteries SET name = 'Архив Daily 4/15', is_active = false "
        "WHERE code = 'daily'"
    )
    for lottery_id, code, name, draw_time in LOTTERIES:
        op.execute(
            f"""
            INSERT INTO lotteries (
                id, code, name, kind, numbers_to_pick, max_number, ticket_price,
                timezone, schedule, sales_cutoff_minutes, is_active,
                next_draw_number, next_ticket_number
            )
            SELECT '{lottery_id}'::uuid, '{code}', '{name}', 'DAILY', 4, 15, NULL,
                'Europe/Moscow', '{{"draw_time":"{draw_time}"}}'::jsonb,
                2, true, 1, 1
            WHERE NOT EXISTS (SELECT 1 FROM lotteries WHERE code='{code}')
            """
        )
        op.execute(
            f"""
            UPDATE lotteries SET name='{name}',
                schedule='{{"draw_time":"{draw_time}"}}'::jsonb,
                sales_cutoff_minutes=2, is_active=true
            WHERE code='{code}'
            """
        )
        for table_name in (
            "jackpot_accounts",
            "distribution_funds",
            "lottery_reserves",
        ):
            account_id = (
                lottery_id[:-3]
                + {
                    "pss": "112",
                    "khan": "118",
                    "pll": "122",
                }[code]
            )
            columns = "id, lottery_id, balance, version"
            values = f"'{account_id}'::uuid, '{lottery_id}'::uuid, 0, 1"
            if table_name == "jackpot_accounts":
                columns += ", base_amount"
                values += ", 0"
            op.execute(
                f"INSERT INTO {table_name} ({columns}) SELECT {values} "
                f"WHERE NOT EXISTS (SELECT 1 FROM {table_name} "
                f"WHERE lottery_id='{lottery_id}'::uuid)"
            )


def downgrade() -> None:
    connection = op.get_bind()
    for lottery_id, code, _name, _draw_time in LOTTERIES:
        has_history = connection.execute(
            sa.text("SELECT 1 FROM draws WHERE lottery_id=CAST(:id AS uuid) LIMIT 1"),
            {"id": lottery_id},
        ).scalar()
        if has_history:
            raise RuntimeError(
                "Cannot remove named lotteries after draw history exists."
            )
        for table_name in (
            "lottery_reserves",
            "distribution_funds",
            "jackpot_accounts",
        ):
            connection.execute(
                sa.text(f"DELETE FROM {table_name} WHERE lottery_id=CAST(:id AS uuid)"),
                {"id": lottery_id},
            )
        connection.execute(
            sa.text("DELETE FROM lotteries WHERE code=:code"), {"code": code}
        )
    op.execute("UPDATE lotteries SET name='Weekly 5/20' WHERE code='weekly'")
    op.execute(
        "UPDATE lotteries SET name='Daily 4/15', is_active=true WHERE code='daily'"
    )
