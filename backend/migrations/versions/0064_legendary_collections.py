"""Bounded gift packs and persistent cosmetic collection, without changing games."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0064_legendary_collections"
down_revision = "0063_rare_achievements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "achievement_rewards",
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "achievement_rewards",
        sa.Column("completed_units", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_foreign_key(
        "fk_achievement_rewards_parent_id_achievement_rewards",
        "achievement_rewards",
        "achievement_rewards",
        ["parent_id"],
        ["id"],
    )
    op.create_index(
        "ix_achievement_rewards_parent_id", "achievement_rewards", ["parent_id"]
    )
    op.create_check_constraint(
        "completed_units_range",
        "achievement_rewards",
        "completed_units BETWEEN 0 AND 500",
    )
    op.execute("""
    CREATE OR REPLACE FUNCTION protect_achievement_history() RETURNS trigger AS $$
    BEGIN
      IF TG_OP='DELETE' THEN RAISE EXCEPTION 'Achievement history is immutable'; END IF;
      IF TG_TABLE_NAME='achievement_awards' THEN
        IF (to_jsonb(NEW)-'reward_status') IS DISTINCT FROM
           (to_jsonb(OLD)-'reward_status') THEN
          RAISE EXCEPTION 'Achievement snapshot is immutable'; END IF;
      ELSE
        IF (to_jsonb(NEW)-'status'-'completed_at'-'retry_at'-'completed_units')
             IS DISTINCT FROM
           (to_jsonb(OLD)-'status'-'completed_at'-'retry_at'-'completed_units')
           OR NEW.completed_units < OLD.completed_units
           OR (NEW.completed_units IS DISTINCT FROM OLD.completed_units
               AND (NEW.payload->>'type' <> 'ticket_pack'
                    OR NEW.completed_units > (NEW.payload->>'amount')::int)) THEN
          RAISE EXCEPTION 'Achievement reward is immutable'; END IF;
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    """)
    op.create_table(
        "collection_unlocks",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            primary_key=True,
        ),
        sa.Column("item", sa.String(80), primary_key=True),
        sa.Column(
            "award_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("achievement_awards.id"),
            nullable=False,
        ),
        sa.Column(
            "unlocked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_table(
        "collection_preferences",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            primary_key=True,
        ),
        sa.Column("active_badge", sa.String(80)),
        sa.Column("active_theme", sa.String(80)),
        sa.ForeignKeyConstraint(
            ["user_id", "active_badge"],
            ["collection_unlocks.user_id", "collection_unlocks.item"],
            name="fk_collection_preferences_badge_unlock",
        ),
        sa.ForeignKeyConstraint(
            ["user_id", "active_theme"],
            ["collection_unlocks.user_id", "collection_unlocks.item"],
            name="fk_collection_preferences_theme_unlock",
        ),
    )
    op.execute("""
    CREATE FUNCTION protect_collection_unlock() RETURNS trigger AS $$
    BEGIN RAISE EXCEPTION 'Collection unlock history is immutable'; END;
    $$ LANGUAGE plpgsql;
    """)
    op.execute("""
    CREATE TRIGGER immutable_collection_unlock
      BEFORE UPDATE OR DELETE ON collection_unlocks
      FOR EACH ROW EXECUTE FUNCTION protect_collection_unlock();
    """)


def downgrade() -> None:
    raise RuntimeError("Gift and cosmetic history requires a forward migration")
