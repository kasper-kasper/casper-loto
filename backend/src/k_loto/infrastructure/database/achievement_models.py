"""Sparse achievement projections, durable work and immutable award snapshots."""

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from k_loto.infrastructure.database.base import Base


class AchievementRuntime(Base):
    __tablename__ = "achievement_runtime"
    __table_args__ = (CheckConstraint("id=1", name="singleton"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="false")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    catalog_revision: Mapped[int] = mapped_column(Integer, server_default="0")
    projection_revision: Mapped[int] = mapped_column(Integer, server_default="0")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_revision: Mapped[int | None] = mapped_column(Integer)
    processing_paused: Mapped[bool] = mapped_column(Boolean, server_default="false")


class AchievementDefinition(Base):
    __tablename__ = "achievement_definitions"
    __table_args__ = (
        CheckConstraint("version > 0", name="version_positive"),
        CheckConstraint(
            "rarity IN ('common','uncommon','rare','epic','legendary')", name="rarity"
        ),
    )
    code: Mapped[str] = mapped_column(String(80), primary_key=True)
    version: Mapped[int] = mapped_column(Integer)
    rarity: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(String(512))
    flavor: Mapped[str | None] = mapped_column(String(512))
    secret: Mapped[bool] = mapped_column(Boolean, server_default="false")
    active: Mapped[bool] = mapped_column(Boolean, server_default="false")
    visible: Mapped[bool] = mapped_column(Boolean, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0")
    icon: Mapped[str | None] = mapped_column(String(512))
    condition: Mapped[dict[str, Any]] = mapped_column(JSONB)
    rewards: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    reward_pending: Mapped[bool] = mapped_column(Boolean, server_default="false")
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AchievementPlayer(Base):
    __tablename__ = "achievement_players"
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    metrics: Mapped[dict[str, int]] = mapped_column(JSONB, server_default="{}")
    last_active_day: Mapped[str | None] = mapped_column(String(10))
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    telegram_enabled: Mapped[bool] = mapped_column(Boolean, server_default="false")
    featured: Mapped[list[str]] = mapped_column(JSONB, server_default="[]")


class AchievementParticipation(Base):
    __tablename__ = "achievement_participations"
    __table_args__ = (CheckConstraint("tickets >= 0", name="nonnegative"),)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    draw_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("draws.id"), primary_key=True
    )
    tickets: Mapped[int] = mapped_column(BigInteger)


class AchievementDay(Base):
    """One sparse row per player/day; indexed best participation progress."""

    __tablename__ = "achievement_days"
    __table_args__ = (
        Index("ix_achievement_day_best_play", "user_id", "play_types"),
        CheckConstraint("play_types BETWEEN 0 AND 3", name="play_types_range"),
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    play_counts: Mapped[dict[str, int]] = mapped_column(JSONB, server_default="{}")
    play_types: Mapped[int] = mapped_column(Integer, server_default="0")
    winning_lotteries: Mapped[list[str]] = mapped_column(JSONB, server_default="[]")


class AchievementWinningDraw(Base):
    """A winning paid participation, regardless of the number of winning tickets."""

    __tablename__ = "achievement_winning_draws"
    __table_args__ = (CheckConstraint("tickets >= 0", name="tickets_nonnegative"),)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    draw_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("draws.id"), primary_key=True
    )
    tickets: Mapped[int] = mapped_column(BigInteger, server_default="0")


class AchievementEvent(Base):
    __tablename__ = "achievement_events"
    __table_args__ = (
        Index(
            "ix_achievement_pending",
            "id",
            postgresql_where=text("processed_at IS NULL"),
        ),
        Index(
            "ix_achievement_player_pending",
            "user_id",
            "id",
            postgresql_where=text("processed_at IS NULL"),
        ),
        Index(
            "ix_achievement_ready",
            "available_at",
            "id",
            postgresql_where=text("processed_at IS NULL"),
        ),
        CheckConstraint("attempts >= 0", name="attempts"),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    event_key: Mapped[str] = mapped_column(String(180), unique=True)
    kind: Mapped[str] = mapped_column(String(32))
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id")
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    cursor: Mapped[str | None] = mapped_column(String(36))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, server_default="0")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.clock_timestamp()
    )
    last_error: Mapped[str | None] = mapped_column(String(80))


class AchievementAward(Base):
    __tablename__ = "achievement_awards"
    __table_args__ = (
        UniqueConstraint("user_id", "code", name="uq_achievement_award_once"),
        Index("ix_achievement_award_player_time", "user_id", "earned_at"),
    )
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    code: Mapped[str] = mapped_column(
        String(80), ForeignKey("achievement_definitions.code")
    )
    version: Mapped[int] = mapped_column(Integer)
    rarity: Mapped[str] = mapped_column(String(16))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reward_status: Mapped[str] = mapped_column(String(16), server_default="pending")
    event_key: Mapped[str] = mapped_column(String(180))


class AchievementReward(Base):
    __tablename__ = "achievement_rewards"
    __table_args__ = (
        CheckConstraint(
            "completed_units BETWEEN 0 AND 500", name="completed_units_range"
        ),
        UniqueConstraint("award_id", "position", name="uq_achievement_reward_part"),
        Index(
            "ix_achievement_reward_pending",
            "id",
            postgresql_where=text("status='pending'"),
        ),
        Index(
            "ix_achievement_reward_waiting",
            "retry_at",
            "id",
            postgresql_where=text("status='waiting'"),
        ),
    )
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    award_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("achievement_awards.id")
    )
    position: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), server_default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    parent_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("achievement_rewards.id"), index=True
    )
    completed_units: Mapped[int] = mapped_column(Integer, server_default="0")


class CollectionUnlock(Base):
    __tablename__ = "collection_unlocks"
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    item: Mapped[str] = mapped_column(String(80), primary_key=True)
    award_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("achievement_awards.id")
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CollectionPreference(Base):
    __tablename__ = "collection_preferences"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "active_badge"],
            ["collection_unlocks.user_id", "collection_unlocks.item"],
            name="fk_collection_preferences_badge_unlock",
        ),
        ForeignKeyConstraint(
            ["user_id", "active_theme"],
            ["collection_unlocks.user_id", "collection_unlocks.item"],
            name="fk_collection_preferences_theme_unlock",
        ),
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    active_badge: Mapped[str | None] = mapped_column(String(80))
    active_theme: Mapped[str | None] = mapped_column(String(80))


class AchievementCorrection(Base):
    __tablename__ = "achievement_corrections"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    event_key: Mapped[str] = mapped_column(String(180), unique=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
