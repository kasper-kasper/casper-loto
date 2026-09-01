"""Start the empty September lottery sequences at one.

Revision ID: 0020_september_numbering
Revises: 0019_september_lottery
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_september_numbering"
down_revision: str | Sequence[str] | None = "0019_september_lottery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    lottery_id = connection.execute(
        sa.text("SELECT id FROM lotteries WHERE code='september' FOR UPDATE")
    ).scalar_one()
    ticket_count = int(
        connection.execute(
            sa.text("SELECT count(*) FROM tickets WHERE lottery_id=:lottery_id"),
            {"lottery_id": lottery_id},
        ).scalar_one()
    )
    if ticket_count:
        raise RuntimeError(
            "September numbering can only be corrected before its first ticket."
        )
    non_scheduled = int(
        connection.execute(
            sa.text(
                "SELECT count(*) FROM draws "
                "WHERE lottery_id=:lottery_id AND status<>'SCHEDULED'"
            ),
            {"lottery_id": lottery_id},
        ).scalar_one()
    )
    if non_scheduled:
        raise RuntimeError(
            "September numbering can only be corrected before its first draw."
        )
    draw_count = int(
        connection.execute(
            sa.text("SELECT count(*) FROM draws WHERE lottery_id=:lottery_id"),
            {"lottery_id": lottery_id},
        ).scalar_one()
    )
    connection.execute(
        sa.text(
            """
            WITH numbered AS (
                SELECT id, row_number() OVER (ORDER BY scheduled_at, id) AS value
                FROM draws
                WHERE lottery_id=:lottery_id
            )
            UPDATE draws AS draw
            SET public_number=numbered.value
            FROM numbered
            WHERE draw.id=numbered.id
            """
        ),
        {"lottery_id": lottery_id},
    )
    connection.execute(
        sa.text(
            """
            UPDATE lotteries
            SET next_draw_number=:next_draw_number, next_ticket_number=1
            WHERE id=:lottery_id
            """
        ),
        {"lottery_id": lottery_id, "next_draw_number": draw_count + 1},
    )


def downgrade() -> None:
    raise RuntimeError("Corrected public numbering must not be reversed.")
