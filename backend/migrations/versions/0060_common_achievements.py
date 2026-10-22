"""Paid combination provenance and unpriced reward configuration."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0060_common_achievements"
down_revision = "0059_achievement_foundation"
branch_labels = None
depends_on = None


# ruff: noqa: E501 -- versioned SQL definitions.
CAPTURE = """
CREATE OR REPLACE FUNCTION capture_achievement_purchase() RETURNS trigger AS $$
DECLARE started timestamptz; batch text;
BEGIN
 SELECT started_at INTO started FROM achievement_runtime WHERE id=1 AND enabled;
 IF started IS NULL THEN RETURN NULL; END IF;
 batch := achievement_batch_id();
 INSERT INTO achievement_events(event_key,kind,user_id,payload)
 SELECT 'purchase:'||batch||':'||user_id||':'||draw_id||':'||coalesce(purchase_operation_id::text,'legacy'), 'purchase',user_id,
 jsonb_build_object('draw',draw_id,'second_draw',second_draw_id,'lottery',lottery_id,'count',count(*),'spent',sum(purchase_price),'manual',count(*) FILTER(WHERE selection_mode='manual' AND source='MANUAL'),'operation',purchase_operation_id)
 FROM achievement_new_tickets WHERE status<>'REFUNDED' AND purchase_price>0
 GROUP BY user_id,draw_id,second_draw_id,lottery_id,purchase_operation_id
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
 SELECT 'refund:'||batch||':'||n.user_id||':'||n.draw_id||':'||coalesce(n.purchase_operation_id::text,'legacy'), 'refund',n.user_id,
 jsonb_build_object('draw',n.draw_id,'second_draw',n.second_draw_id,'lottery',n.lottery_id,'count',count(*),'spent',sum(n.purchase_price),'manual',count(*) FILTER(WHERE n.selection_mode='manual' AND n.source='MANUAL'),'operation',n.purchase_operation_id)
 FROM achievement_new_tickets n JOIN achievement_old_tickets o USING(id)
 WHERE n.status='REFUNDED' AND o.status<>'REFUNDED' AND n.purchased_at>=started AND n.purchase_price>0
 GROUP BY n.user_id,n.draw_id,n.second_draw_id,n.lottery_id,n.purchase_operation_id
 ON CONFLICT(event_key) DO UPDATE SET payload=achievement_events.payload ||
 jsonb_build_object('count',(achievement_events.payload->>'count')::bigint+(EXCLUDED.payload->>'count')::bigint,
 'spent',(achievement_events.payload->>'spent')::bigint+(EXCLUDED.payload->>'spent')::bigint,'manual',coalesce((achievement_events.payload->>'manual')::bigint,0)+coalesce((EXCLUDED.payload->>'manual')::bigint,0));
 RETURN NULL;
END; $$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    op.create_index(
        "ix_achievement_unseen_notifications",
        "user_notifications",
        ["user_id", "created_at", "id"],
        postgresql_where=sa.text("type='ACHIEVEMENT' AND read_at IS NULL"),
    )
    op.add_column(
        "tickets",
        sa.Column(
            "selection_mode", sa.String(16), nullable=False, server_default="unknown"
        ),
    )
    op.add_column(
        "tickets", sa.Column("purchase_operation_id", postgresql.UUID(as_uuid=True))
    )
    op.create_check_constraint(
        "ticket_selection_mode",
        "tickets",
        "selection_mode IN ('unknown','manual','random')",
    )
    op.create_index(
        "ix_ticket_purchase_operation",
        "tickets",
        ["purchase_operation_id"],
        postgresql_where=sa.text("purchase_operation_id IS NOT NULL"),
    )
    op.add_column(
        "achievement_definitions",
        sa.Column(
            "reward_pending", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    for statement in CAPTURE.split("-- next --"):
        if statement.lstrip().startswith(
            "CREATE OR REPLACE FUNCTION capture_achievement_"
        ):
            op.execute(statement)
    op.execute("""
    CREATE FUNCTION protect_ticket_selection() RETURNS trigger AS $$
    BEGIN
      IF NEW.selection_mode IS DISTINCT FROM OLD.selection_mode
         OR NEW.purchase_operation_id IS DISTINCT FROM OLD.purchase_operation_id THEN
        RAISE EXCEPTION 'Ticket purchase provenance is immutable';
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE TRIGGER trg_ticket_selection_immutable BEFORE UPDATE ON tickets
    FOR EACH ROW EXECUTE FUNCTION protect_ticket_selection();
    """)


def downgrade() -> None:
    raise RuntimeError("Purchase provenance is immutable; use a forward migration")
