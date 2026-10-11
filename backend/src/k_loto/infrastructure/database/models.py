"""Persistent K-Loto domain model."""

from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from k_loto.domain.enums import (
    AuditAction,
    DrawStatus,
    InAppNotificationType,
    InterestingFactStatus,
    LedgerAccountKind,
    LotteryKind,
    NotificationStatus,
    NotificationType,
    TicketSource,
    TicketStatus,
    TransactionType,
)
from k_loto.infrastructure.database.base import Base


def enum_type(enum: type[Any], name: str) -> Enum:
    return Enum(enum, name=name, native_enum=False, create_constraint=True, length=32)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )


class WebAccount(TimestampMixin, Base):
    """Password credential for the ordinary browser client."""

    __tablename__ = "web_accounts"
    __table_args__ = (
        CheckConstraint("char_length(username) >= 3", name="username_min_length"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        unique=True,
    )
    username: Mapped[str] = mapped_column(String(128), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WebLoginToken(Base):
    """Short-lived one-time browser login issued to a Telegram player."""

    __tablename__ = "web_login_tokens"
    __table_args__ = (
        CheckConstraint("char_length(token_hash) = 64", name="token_hash_length"),
        Index("ix_web_login_tokens_expires_at", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Lottery(TimestampMixin, Base):
    __tablename__ = "lotteries"
    __table_args__ = (
        CheckConstraint("numbers_to_pick > 0", name="numbers_to_pick_positive"),
        CheckConstraint("max_number >= numbers_to_pick", name="max_number_valid"),
        CheckConstraint(
            "ticket_price IS NULL OR ticket_price > 0", name="ticket_price_positive"
        ),
        CheckConstraint("next_draw_number >= 1", name="next_draw_number_positive"),
        CheckConstraint("next_ticket_number >= 1", name="next_ticket_number_positive"),
        CheckConstraint("char_length(ruleset_code) > 0", name="ruleset_code_not_empty"),
        Index("ix_lotteries_ruleset_code", "ruleset_code"),
        CheckConstraint(
            "max_tickets_per_purchase BETWEEN 1 AND 1000",
            name="max_tickets_per_purchase_valid",
        ),
        CheckConstraint(
            "max_tickets_per_user_per_draw >= max_tickets_per_purchase",
            name="max_tickets_per_user_per_draw_valid",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    kind: Mapped[LotteryKind] = mapped_column(enum_type(LotteryKind, "lottery_kind"))
    ruleset_code: Mapped[str] = mapped_column(String(64))
    numbers_to_pick: Mapped[int] = mapped_column(Integer)
    max_number: Mapped[int] = mapped_column(Integer)
    ticket_price: Mapped[int | None] = mapped_column(BigInteger)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    schedule: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    sales_cutoff_minutes: Mapped[int | None] = mapped_column(Integer)
    max_tickets_per_purchase: Mapped[int] = mapped_column(
        Integer, default=1000, server_default="1000"
    )
    max_tickets_per_user_per_draw: Mapped[int] = mapped_column(
        Integer, default=5000, server_default="5000"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    next_draw_number: Mapped[int] = mapped_column(
        BigInteger, default=1, server_default="1"
    )
    next_ticket_number: Mapped[int] = mapped_column(
        BigInteger, default=1, server_default="1"
    )


class FavoriteCombination(TimestampMixin, Base):
    """A reusable number selection owned by one player and lottery."""

    __tablename__ = "favorite_combinations"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "lottery_id",
            "numbers",
            name="uq_favorite_user_lottery_numbers",
        ),
        CheckConstraint("cardinality(numbers) > 0", name="numbers_not_empty"),
        Index("ix_favorite_user_lottery", "user_id", "lottery_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    lottery_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lotteries.id", ondelete="RESTRICT")
    )
    numbers: Mapped[list[int]] = mapped_column(ARRAY(Integer))


class Draw(TimestampMixin, Base):
    __tablename__ = "draws"
    __table_args__ = (
        UniqueConstraint("lottery_id", "public_number", name="uq_draw_lottery_number"),
        CheckConstraint("public_number >= 1", name="public_number_positive"),
        CheckConstraint(
            "sales_close_at <= scheduled_at", name="sales_close_before_draw"
        ),
        CheckConstraint("ticket_count >= 0", name="ticket_count_nonnegative"),
        CheckConstraint("total_sales >= 0", name="total_sales_nonnegative"),
        CheckConstraint("total_payout >= 0", name="total_payout_nonnegative"),
        CheckConstraint(
            "distributed_amount >= 0", name="distributed_amount_nonnegative"
        ),
        CheckConstraint("kasper_fund_used >= 0", name="kasper_fund_used_nonnegative"),
        Index("ix_draw_due", "status", "scheduled_at"),
        Index(
            "ix_draw_lottery_status_scheduled", "lottery_id", "status", "scheduled_at"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    lottery_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lotteries.id", ondelete="RESTRICT")
    )
    public_number: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[DrawStatus] = mapped_column(
        enum_type(DrawStatus, "draw_status"),
        default=DrawStatus.SCHEDULED,
        server_default=DrawStatus.SCHEDULED.value,
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sales_close_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    winning_numbers: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    correlation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), default=uuid4, unique=True
    )
    ticket_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_sales: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    total_payout: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    jackpot_opening: Mapped[int | None] = mapped_column(BigInteger)
    jackpot_closing: Mapped[int | None] = mapped_column(BigInteger)
    distribution_opening: Mapped[int | None] = mapped_column(BigInteger)
    distribution_closing: Mapped[int | None] = mapped_column(BigInteger)
    reserve_used: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    kasper_fund_used: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0"
    )
    configuration_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )

    is_distribution: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    distribution_category: Mapped[str | None] = mapped_column(String(32))
    distributed_amount: Mapped[int] = mapped_column(
        BigInteger, default=0, server_default="0"
    )


class DistributionAnnouncement(Base):
    __tablename__ = "distribution_announcements"
    __table_args__ = (
        UniqueConstraint(
            "draw_id", "kind", name="uq_distribution_announcement_draw_kind"
        ),
        CheckConstraint(
            "kind IN ('schedule','result')", name="distribution_announcement_kind"
        ),
        Index("ix_distribution_announcement_delivery", "state", "retry_after"),
        CheckConstraint(
            "state IN ('queued','sending','sent','uncertain','failed','expired')",
            name="ck_distribution_announcement_state",
        ),
    )
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    draw_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("draws.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(
        String(16), default="schedule", server_default="schedule"
    )
    text: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(
        String(16), default="queued", server_default="queued"
    )
    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    message_id: Mapped[int | None] = mapped_column(BigInteger)
    error_type: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint(
            "lottery_id", "public_number", name="uq_ticket_lottery_number"
        ),
        CheckConstraint("public_number >= 1", name="public_number_positive"),
        CheckConstraint("purchase_price > 0", name="purchase_price_positive"),
        CheckConstraint("prize_amount >= 0", name="prize_amount_nonnegative"),
        CheckConstraint("matches IS NULL OR matches >= 0", name="matches_nonnegative"),
        Index("ix_ticket_user_status", "user_id", "status"),
        Index("ix_ticket_user_draw_status", "user_id", "draw_id", "status"),
        Index("ix_ticket_draw", "draw_id"),
        Index("ix_ticket_second_draw", "second_draw_id"),
        CheckConstraint(
            "second_draw_id IS NULL OR second_draw_id <> draw_id",
            name="distinct_dual_draws",
        ),
        CheckConstraint(
            "dual_night_matches IS NULL OR dual_night_matches BETWEEN 0 AND 2",
            name="dual_night_matches",
        ),
        CheckConstraint(
            "dual_dawn_matches IS NULL OR dual_dawn_matches BETWEEN 0 AND 2",
            name="dual_dawn_matches",
        ),
        Index("ix_ticket_status_settled_lottery", "status", "settled_at", "lottery_id"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    public_number: Mapped[int] = mapped_column(BigInteger)
    lottery_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lotteries.id", ondelete="RESTRICT")
    )
    draw_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("draws.id", ondelete="RESTRICT")
    )
    second_draw_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("draws.id", ondelete="RESTRICT")
    )
    dual_night_matches: Mapped[int | None] = mapped_column(Integer)
    dual_dawn_matches: Mapped[int | None] = mapped_column(Integer)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    numbers: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    purchase_price: Mapped[int] = mapped_column(BigInteger)
    source: Mapped[TicketSource] = mapped_column(
        enum_type(TicketSource, "ticket_source"),
        default=TicketSource.MANUAL,
        server_default=TicketSource.MANUAL.value,
    )
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[TicketStatus] = mapped_column(
        enum_type(TicketStatus, "ticket_status"),
        default=TicketStatus.PURCHASED,
        server_default=TicketStatus.PURCHASED.value,
    )
    matches: Mapped[int | None] = mapped_column(Integer)
    prize_amount: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bingo_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class InstantTicket(Base):
    """Immutable, immediately settled ticket for Kasper LIVE."""

    __tablename__ = "instant_tickets"
    __table_args__ = (
        CheckConstraint("public_number >= 1", name="public_number_positive"),
        CheckConstraint("purchase_price > 0", name="purchase_price_positive"),
        CheckConstraint("prize_amount >= 0", name="prize_amount_nonnegative"),
        CheckConstraint("cardinality(symbols) = 3", name="three_symbols"),
        Index("ix_instant_ticket_user_purchased", "user_id", "purchased_at"),
        Index("ix_instant_ticket_purchased", "purchased_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    public_number: Mapped[int] = mapped_column(
        BigInteger, Identity(start=1), unique=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    symbols: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    purchase_price: Mapped[int] = mapped_column(BigInteger)
    prize_amount: Mapped[int] = mapped_column(BigInteger)
    odds_version: Mapped[str] = mapped_column(String(32))
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    settled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BingoPoolTicket(Base):
    """Preprinted draw inventory; a claimed entry references an immutable ticket."""

    __tablename__ = "bingo_pool_tickets"
    __table_args__ = (
        UniqueConstraint("draw_id", "pool_position", name="uq_bingo_pool_position"),
        CheckConstraint("pool_position >= 1", name="bingo_pool_position_positive"),
        CheckConstraint("cardinality(numbers) = 12", name="bingo_twelve_numbers"),
        Index("ix_bingo_pool_free", "draw_id", "ticket_id"),
    )
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    draw_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("draws.id", ondelete="RESTRICT")
    )
    pool_position: Mapped[int] = mapped_column(BigInteger)
    numbers: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    ticket_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tickets.id", ondelete="RESTRICT"), unique=True
    )


class Balance(TimestampMixin, Base):
    __tablename__ = "balances"
    __table_args__ = (CheckConstraint("amount >= 0", name="amount_nonnegative"),)

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    amount: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class JackpotAccount(TimestampMixin, Base):
    __tablename__ = "jackpot_accounts"
    __table_args__ = (
        CheckConstraint("balance >= 0", name="balance_nonnegative"),
        CheckConstraint("base_amount >= 0", name="base_amount_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    lottery_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lotteries.id", ondelete="RESTRICT"),
        unique=True,
    )
    balance: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    base_amount: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class DistributionFund(TimestampMixin, Base):
    __tablename__ = "distribution_funds"
    __table_args__ = (CheckConstraint("balance >= 0", name="balance_nonnegative"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    lottery_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lotteries.id", ondelete="RESTRICT"),
        unique=True,
    )
    balance: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class LotteryReserve(TimestampMixin, Base):
    __tablename__ = "lottery_reserves"
    __table_args__ = (CheckConstraint("balance >= 0", name="balance_nonnegative"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    lottery_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lotteries.id", ondelete="RESTRICT"),
        unique=True,
    )
    balance: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class KasperFundAccount(TimestampMixin, Base):
    """Singleton source for ordinary prizes and base-jackpot resets."""

    __tablename__ = "kasper_fund_accounts"
    __table_args__ = (CheckConstraint("balance >= 0", name="balance_nonnegative"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    balance: Mapped[int] = mapped_column(BigInteger)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class JackpotWinEvent(Base):
    """Immutable projection of a jackpot win for inbox news and analytics."""

    __tablename__ = "jackpot_win_events"
    __table_args__ = (
        CheckConstraint("jackpot_amount > 0", name="amount_positive"),
        CheckConstraint("winner_ticket_count > 0", name="ticket_count_positive"),
        CheckConstraint("winner_user_count > 0", name="user_count_positive"),
        Index("ix_jackpot_win_occurred", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    draw_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("draws.id", ondelete="RESTRICT"), unique=True
    )
    lottery_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lotteries.id", ondelete="RESTRICT")
    )
    jackpot_amount: Mapped[int] = mapped_column(BigInteger)
    winner_ticket_count: Mapped[int] = mapped_column(Integer)
    winner_user_count: Mapped[int] = mapped_column(Integer)
    base_jackpot_after: Mapped[int] = mapped_column(BigInteger)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"
    __table_args__ = (
        CheckConstraint("amount <> 0", name="amount_nonzero"),
        CheckConstraint(
            "balance_after = balance_before + amount", name="balance_equation"
        ),
        CheckConstraint("balance_before >= 0", name="balance_before_nonnegative"),
        CheckConstraint("balance_after >= 0", name="balance_after_nonnegative"),
        Index("ix_ledger_created_at", "created_at"),
        Index("ix_ledger_user_created", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    operation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True)
    account_kind: Mapped[LedgerAccountKind] = mapped_column(
        enum_type(LedgerAccountKind, "ledger_account_kind")
    )
    account_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    type: Mapped[TransactionType] = mapped_column(
        enum_type(TransactionType, "transaction_type")
    )
    amount: Mapped[int] = mapped_column(BigInteger)
    balance_before: Mapped[int] = mapped_column(BigInteger)
    balance_after: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    lottery_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lotteries.id", ondelete="RESTRICT")
    )
    draw_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("draws.id", ondelete="RESTRICT")
    )
    ticket_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tickets.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    details: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"
    __table_args__ = (Index("ix_admin_audit_created", "created_at"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    admin_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    action: Mapped[AuditAction] = mapped_column(enum_type(AuditAction, "audit_action"))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    old_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    new_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        CheckConstraint("attempts >= 0", name="attempts_nonnegative"),
        Index("ix_notification_outbox_dispatch", "status", "available_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    event_key: Mapped[str] = mapped_column(String(180), unique=True)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    type: Mapped[NotificationType] = mapped_column(
        enum_type(NotificationType, "notification_type")
    )
    status: Mapped[NotificationStatus] = mapped_column(
        enum_type(NotificationStatus, "notification_status"),
        default=NotificationStatus.PENDING,
        server_default=NotificationStatus.PENDING.value,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class UserNotificationPreference(TimestampMixin, Base):
    """Explicit Telegram delivery consent and reminder preferences."""

    __tablename__ = "user_notification_preferences"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    telegram_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    draw_results_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    inactivity_reminders_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    write_access_granted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_inactivity_reminder_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class UserNotification(Base):
    """Durable in-app inbox; only its read marker may change."""

    __tablename__ = "user_notifications"
    __table_args__ = (Index("ix_user_notification_inbox", "user_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    event_key: Mapped[str] = mapped_column(String(180), unique=True)
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    type: Mapped[InAppNotificationType] = mapped_column(
        enum_type(InAppNotificationType, "in_app_notification_type")
    )
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(String(512))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AutoPlaySetting(TimestampMixin, Base):
    """Recurring auto-entry instruction for all active lotteries."""

    __tablename__ = "auto_play_settings"
    __table_args__ = (
        CheckConstraint(
            "tickets_per_draw BETWEEN 1 AND 5", name="tickets_per_draw_valid"
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    tickets_per_draw: Mapped[int] = mapped_column(
        Integer, default=5, server_default="5"
    )
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_succeeded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(128))


class SchedulerHeartbeat(Base):
    """Singleton persisted health projection for scheduler observability."""

    __tablename__ = "scheduler_heartbeat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_succeeded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(256))
    settled_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    prepared_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class InterestingFactBatch(Base):
    """One immutable marker per Moscow generation day."""

    __tablename__ = "interesting_fact_batches"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    generation_date: Mapped[date] = mapped_column(Date, unique=True)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Publication(TimestampMixin, Base):
    """Owner-authored content; published snapshots never change in place."""

    __tablename__ = "publications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')", name="publication_status"
        ),
        CheckConstraint("revision >= 1", name="publication_revision"),
        CheckConstraint(
            "event_mode IS NULL OR event_mode IN ('automatic', 'draft')",
            name="publication_event_mode",
        ),
        UniqueConstraint("event_key", name="uq_publication_event_key"),
        Index("ix_publications_event_type", "event_type", "created_at"),
        Index("ix_publications_feed", "status", "published_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    author_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    lottery_code: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(
        String(16), default="draft", server_default="draft"
    )
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    event_type: Mapped[str | None] = mapped_column(String(12))
    event_key: Mapped[str | None] = mapped_column(String(180))
    event_mode: Mapped[str | None] = mapped_column(String(16))


class PublicationEventState(TimestampMixin, Base):
    """Content-only checkpoints/records; never authoritative financial balances."""

    __tablename__ = "publication_event_states"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB)


class InterestingFact(Base):
    """Precomputed Telegram-content candidate; status is owner workflow state."""

    __tablename__ = "interesting_facts"
    __table_args__ = (
        UniqueConstraint(
            "generation_date",
            "lottery_id",
            "fact_type",
            name="uq_interesting_fact_daily_type",
        ),
        CheckConstraint("score BETWEEN 0 AND 100", name="score_valid"),
        CheckConstraint(
            "status IN ('new', 'viewed', 'used', 'hidden')",
            name="interesting_fact_status",
        ),
        Index(
            "ix_interesting_facts_admin",
            "status",
            "generation_date",
            "score",
        ),
        Index("ix_interesting_facts_lottery", "lottery_id", "generation_date"),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    batch_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("interesting_fact_batches.id", ondelete="RESTRICT"),
    )
    generation_date: Mapped[date] = mapped_column(Date)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    lottery_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lotteries.id", ondelete="RESTRICT")
    )
    fact_type: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(String(600))
    numeric_values: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    score: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(32),
        default=InterestingFactStatus.NEW,
        server_default=InterestingFactStatus.NEW.value,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
