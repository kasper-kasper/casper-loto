"""Apply the PSS Casper Ball format explicitly after the interrupted transition."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0045_force_pss_casper_ball"
down_revision: str | Sequence[str] | None = "0044_finish_pss_casper_ball"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RULESET = "casper_ball_5_36_1_8"


def upgrade() -> None:
    connection = op.get_bind()
    lottery_id = connection.execute(sa.text("SELECT id FROM lotteries WHERE code='pss' FOR UPDATE")).scalar_one_or_none()
    if lottery_id is None:
        raise RuntimeError("PSS lottery is missing; refusing to apply Casper Ball format.")
    connection.execute(sa.text("""
        UPDATE lotteries
        SET name='Casper Ball', ruleset_code='casper_ball_5_36_1_8', numbers_to_pick=6, max_number=44, updated_at=now()
        WHERE id=:lottery_id
    """), {"lottery_id": lottery_id})
    ticket_price = connection.execute(sa.text("SELECT ticket_price FROM lotteries WHERE id=:lottery_id"), {"lottery_id": lottery_id}).scalar_one()
    connection.execute(sa.text("""
        UPDATE draws
        SET configuration_snapshot=jsonb_build_object(
            'ruleset_code', 'casper_ball_5_36_1_8', 'ticket_price', :ticket_price,
            'numbers_to_pick', 6, 'max_number', 44, 'base_jackpot', 50000000
        ), updated_at=now()
        WHERE lottery_id=:lottery_id AND status='SCHEDULED'
    """), {"lottery_id": lottery_id, "ticket_price": ticket_price})
    current = connection.execute(sa.text("SELECT ruleset_code, numbers_to_pick, max_number FROM lotteries WHERE id=:lottery_id"), {"lottery_id": lottery_id}).mappings().one()
    if (current["ruleset_code"], current["numbers_to_pick"], current["max_number"]) != (RULESET, 6, 44):
        raise RuntimeError(f"PSS format update did not persist: {dict(current)}")


def downgrade() -> None:
    raise RuntimeError("PSS Casper Ball format is irreversible.")
