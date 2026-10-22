"""Sparse daily and winning-draw achievement projections; optional flavor copy."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0062_uncommon_achievements"
down_revision = "0061_achievement_rewards"
branch_labels = None
depends_on = None

# ruff: noqa: E501 -- frozen SQL capture, no changes to gameplay or ledger.
CAPTURE_DAYS = """
CREATE OR REPLACE FUNCTION capture_achievement_purchase() RETURNS trigger AS $$
DECLARE started timestamptz; batch text;
BEGIN
 SELECT started_at INTO started FROM achievement_runtime WHERE id=1 AND enabled;
 IF started IS NULL THEN RETURN NULL; END IF;
 batch := achievement_batch_id();
 INSERT INTO achievement_events(event_key,kind,user_id,payload)
 SELECT 'purchase:'||batch||':'||user_id||':'||draw_id||':'||coalesce(purchase_operation_id::text,'legacy')||':'||(purchased_at AT TIME ZONE 'Europe/Moscow')::date::text, 'purchase',user_id,
 jsonb_build_object('draw',draw_id,'second_draw',second_draw_id,'lottery',lottery_id,'count',count(*),'spent',sum(purchase_price),'manual',count(*) FILTER(WHERE selection_mode='manual' AND source='MANUAL'),'operation',purchase_operation_id,'day',(purchased_at AT TIME ZONE 'Europe/Moscow')::date)
 FROM achievement_new_tickets WHERE status<>'REFUNDED' AND purchase_price>0
 GROUP BY user_id,draw_id,second_draw_id,lottery_id,purchase_operation_id,(purchased_at AT TIME ZONE 'Europe/Moscow')::date
 ON CONFLICT(event_key) DO UPDATE SET payload=achievement_events.payload ||
 jsonb_build_object('count',(achievement_events.payload->>'count')::bigint+(EXCLUDED.payload->>'count')::bigint,
 'spent',(achievement_events.payload->>'spent')::bigint+(EXCLUDED.payload->>'spent')::bigint,'manual',coalesce((achievement_events.payload->>'manual')::bigint,0)+coalesce((EXCLUDED.payload->>'manual')::bigint,0));
 RETURN NULL;
END; $$ LANGUAGE plpgsql;
-- next --
CREATE OR REPLACE FUNCTION capture_achievement_refund() RETURNS trigger AS $$
DECLARE started timestamptz; batch text;
BEGIN
 SELECT started_at INTO started FROM achievement_runtime WHERE id=1 AND enabled;
 IF started IS NULL THEN RETURN NULL; END IF;
 batch := achievement_batch_id();
 INSERT INTO achievement_events(event_key,kind,user_id,payload)
 SELECT 'refund:'||batch||':'||n.user_id||':'||n.draw_id||':'||coalesce(n.purchase_operation_id::text,'legacy')||':'||(n.purchased_at AT TIME ZONE 'Europe/Moscow')::date::text, 'refund',n.user_id,
 jsonb_build_object('draw',n.draw_id,'second_draw',n.second_draw_id,'lottery',n.lottery_id,'count',count(*),'spent',sum(n.purchase_price),'manual',count(*) FILTER(WHERE n.selection_mode='manual' AND n.source='MANUAL'),'operation',n.purchase_operation_id,'day',(n.purchased_at AT TIME ZONE 'Europe/Moscow')::date)
 FROM achievement_new_tickets n JOIN achievement_old_tickets o USING(id)
 WHERE n.status='REFUNDED' AND o.status<>'REFUNDED' AND n.purchased_at>=started AND n.purchase_price>0
 GROUP BY n.user_id,n.draw_id,n.second_draw_id,n.lottery_id,n.purchase_operation_id,(n.purchased_at AT TIME ZONE 'Europe/Moscow')::date
 ON CONFLICT(event_key) DO UPDATE SET payload=achievement_events.payload ||
 jsonb_build_object('count',(achievement_events.payload->>'count')::bigint+(EXCLUDED.payload->>'count')::bigint,
 'spent',(achievement_events.payload->>'spent')::bigint+(EXCLUDED.payload->>'spent')::bigint,'manual',coalesce((achievement_events.payload->>'manual')::bigint,0)+coalesce((EXCLUDED.payload->>'manual')::bigint,0));
 RETURN NULL;
END; $$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    op.add_column(
        "achievement_runtime",
        sa.Column(
            "projection_revision", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column("achievement_definitions", sa.Column("flavor", sa.String(512)))
    op.create_table(
        "achievement_days",
        sa.Column(
            "user_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            primary_key=True,
        ),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("play_counts", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column("play_types", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("winning_lotteries", pg.JSONB(), nullable=False, server_default="[]"),
        sa.CheckConstraint("play_types BETWEEN 0 AND 3", name="play_types_range"),
    )
    op.create_index(
        "ix_achievement_day_best_play", "achievement_days", ["user_id", "play_types"]
    )
    op.create_table(
        "achievement_winning_draws",
        sa.Column(
            "user_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            primary_key=True,
        ),
        sa.Column(
            "draw_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("draws.id"),
            primary_key=True,
        ),
    )
    for statement in CAPTURE_DAYS.split("-- next --"):
        op.execute(statement)


def downgrade() -> None:
    raise RuntimeError("Preserve achievement progress; use a forward migration")
