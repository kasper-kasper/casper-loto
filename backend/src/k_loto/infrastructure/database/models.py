"""Persistent K-Loto domain model."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from k_loto.domain.enums import (
    AuditAction,
    DrawStatus,
    LedgerAccountKind,
    LotteryKind,
    NotificationStatus,
    NotificationType,
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
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    kind: Mapped[LotteryKind] = mapped_column(enum_type(LotteryKind, "lottery_kind"))
    numbers_to_pick: Mapped[int] = mapped_column(Integer)
    max_number: Mapped[int] = mapped_column(Integer)
    ticket_price: Mapped[int | None] = mapped_column(BigInteger)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")
    schedule: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    sales_cutoff_minutes: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    next_draw_number: Mapped[int] = mapped_column(
        BigInteger, default=1, server_default="1"
    )
    next_ticket_number: Mapped[int] = mapped_column(
        BigInteger, default=1, server_default="1"
    )


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
        Index("ix_draw_due", "status", "scheduled_at"),
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
        Index("ix_ticket_draw", "draw_id"),
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
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    numbers: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    purchase_price: Mapped[int] = mapped_column(BigInteger)
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
