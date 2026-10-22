"""Funded achievement gifts, durable deferred delivery and planned cases."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0061_achievement_rewards"
down_revision = "0060_common_achievements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "achievement_rewards", sa.Column("retry_at", sa.DateTime(timezone=True))
    )
    op.create_index(
        "ix_achievement_reward_waiting",
        "achievement_rewards",
        ["retry_at", "id"],
        postgresql_where=sa.text("status='waiting'"),
    )
    op.add_column(
        "tickets", sa.Column("achievement_reward_id", postgresql.UUID(as_uuid=True))
    )
    op.create_foreign_key(
        "fk_tickets_achievement_reward_id_achievement_rewards",
        "tickets",
        "achievement_rewards",
        ["achievement_reward_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_tickets_achievement_reward_id", "tickets", ["achievement_reward_id"]
    )
    op.drop_constraint(op.f("ck_tickets_ticket_source"), "tickets", type_="check")
    op.create_check_constraint(
        "ticket_source", "tickets", "source IN ('MANUAL','AUTO_PLAY','GIFT')"
    )
    op.drop_constraint(
        op.f("ck_tickets_purchase_price_positive"), "tickets", type_="check"
    )
    op.create_check_constraint(
        "purchase_price_positive", "tickets", "purchase_price>=0"
    )
    op.create_check_constraint(
        "gift_ticket_origin",
        "tickets",
        "(source='GIFT' AND purchase_price=0 AND achievement_reward_id IS NOT NULL "
        "AND selection_mode='random') OR (source<>'GIFT' AND purchase_price>0 "
        "AND achievement_reward_id IS NULL)",
    )
    op.execute("""
    CREATE OR REPLACE FUNCTION protect_ticket_selection() RETURNS trigger AS $$
    BEGIN
      IF NEW.selection_mode IS DISTINCT FROM OLD.selection_mode
         OR NEW.purchase_operation_id IS DISTINCT FROM OLD.purchase_operation_id
         OR NEW.achievement_reward_id IS DISTINCT FROM OLD.achievement_reward_id THEN
        RAISE EXCEPTION 'Ticket purchase provenance is immutable';
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE OR REPLACE FUNCTION protect_achievement_history() RETURNS trigger AS $$
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Achievement history is immutable'; END IF;
      IF TG_TABLE_NAME='achievement_awards' THEN
        IF (to_jsonb(NEW)-'reward_status') IS DISTINCT FROM
           (to_jsonb(OLD)-'reward_status') THEN
          RAISE EXCEPTION 'Achievement snapshot is immutable'; END IF;
      ELSE
        IF (to_jsonb(NEW)-'status'-'completed_at'-'retry_at') IS DISTINCT FROM
           (to_jsonb(OLD)-'status'-'completed_at'-'retry_at') THEN
          RAISE EXCEPTION 'Achievement reward is immutable'; END IF;
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    raise RuntimeError("Reward and gift history is immutable; use a forward migration")
