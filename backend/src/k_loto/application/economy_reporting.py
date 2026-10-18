"""Read-only CAS flows, grouped by complete ledger operations and Moscow days."""

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import FromClause, Select

from k_loto.domain.enums import LedgerAccountKind, TransactionType
from k_loto.domain.schedules import MOSCOW
from k_loto.infrastructure.database.models import LedgerTransaction


@dataclass(frozen=True)
class EconomyDay:
    day: date
    included: bool = True
    partial: bool = False
    credited: int = 0
    debited: int = 0
    prizes: int = 0
    refunds: int = 0
    admin_credit: int = 0
    admin_debit: int = 0
    purchases: int = 0
    issued: int = 0
    burned: int = 0
    fund_credited: int = 0
    fund_debited: int = 0

    def payload(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "player_net": self.credited - self.debited,
            "supply_net": self.issued - self.burned,
            "fund_net": self.fund_credited - self.fund_debited,
            "other_credit": self.credited
            - self.prizes
            - self.refunds
            - self.admin_credit,
            "other_debit": self.debited - self.purchases - self.admin_debit,
        }


def daily_flows_query(
    ledger: FromClause,
    *,
    start: datetime,
    end: datetime,
    epoch_started: datetime | None,
    archive: bool,
) -> Select[Any]:
    # The date index bounds candidate operations. Aggregate ALL rows of each
    # operation before testing date/epoch: a transfer crossing midnight or the
    # epoch boundary must never become spurious issuance or burning.
    candidates = (
        select(ledger.c.operation_id)
        .where(ledger.c.created_at >= start, ledger.c.created_at < end)
        .distinct()
    )
    if epoch_started is not None:
        candidates = candidates.where(
            ledger.c.created_at < epoch_started
            if archive
            else ledger.c.created_at >= epoch_started
        )
    user = ledger.c.account_kind == LedgerAccountKind.USER_BALANCE
    positive = user & (ledger.c.amount > 0)
    negative = user & (ledger.c.amount < 0)

    def total(condition: Any, amount: Any) -> Any:
        return func.sum(case((condition, amount), else_=0))

    operation = (
        select(
            ledger.c.operation_id,
            func.min(ledger.c.created_at).label("happened_at"),
            func.sum(ledger.c.amount).label("supply_net"),
            total(positive, ledger.c.amount).label("credited"),
            total(negative, -ledger.c.amount).label("debited"),
            total(
                positive
                & ledger.c.type.in_(
                    (TransactionType.PRIZE_PAYOUT, TransactionType.JACKPOT_PAYOUT)
                ),
                ledger.c.amount,
            ).label("prizes"),
            total(
                positive & (ledger.c.type == TransactionType.TICKET_REFUND),
                ledger.c.amount,
            ).label("refunds"),
            total(
                positive & (ledger.c.type == TransactionType.ADMIN_BALANCE_ADJUSTMENT),
                ledger.c.amount,
            ).label("admin_credit"),
            total(
                negative & (ledger.c.type == TransactionType.ADMIN_BALANCE_ADJUSTMENT),
                -ledger.c.amount,
            ).label("admin_debit"),
            total(
                negative & (ledger.c.type == TransactionType.TICKET_PURCHASE),
                -ledger.c.amount,
            ).label("purchases"),
            total(
                (ledger.c.account_kind == LedgerAccountKind.KASPER_FUND)
                & (ledger.c.amount > 0),
                ledger.c.amount,
            ).label("fund_credited"),
            total(
                (ledger.c.account_kind == LedgerAccountKind.KASPER_FUND)
                & (ledger.c.amount < 0),
                -ledger.c.amount,
            ).label("fund_debited"),
        )
        .where(ledger.c.operation_id.in_(candidates))
        .group_by(ledger.c.operation_id)
        .subquery()
    )
    day = func.date(func.timezone("Europe/Moscow", operation.c.happened_at))
    statement = select(
        day.label("day"),
        *(
            func.sum(operation.c[name]).label(name)
            for name in (
                "credited",
                "debited",
                "prizes",
                "refunds",
                "admin_credit",
                "admin_debit",
                "purchases",
                "fund_credited",
                "fund_debited",
            )
        ),
        total(operation.c.supply_net > 0, operation.c.supply_net).label("issued"),
        total(operation.c.supply_net < 0, -operation.c.supply_net).label("burned"),
    ).where(operation.c.happened_at >= start, operation.c.happened_at < end)
    if epoch_started is not None:
        statement = statement.where(
            operation.c.happened_at < epoch_started
            if archive
            else operation.c.happened_at >= epoch_started
        )
    return statement.group_by(day).order_by(day)


class EconomyReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def daily(
        self,
        *,
        days: int = 7,
        through: date | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        today = (now or datetime.now(UTC)).astimezone(MOSCOW).date()
        selected = through or today
        if days not in (7, 30) or selected > today:
            raise ValueError(
                "Choose 7 or 30 days ending no later than today in Moscow."
            )
        first = selected - timedelta(days=days - 1)
        start = datetime.combine(first, time.min, MOSCOW).astimezone(UTC)
        end = datetime.combine(
            selected + timedelta(days=1), time.min, MOSCOW
        ).astimezone(UTC)
        epoch_started = self.session.info.get("economy_started_at")
        epoch, scope = self.session.info.get("economy_scope", (1, "current"))
        # Core table access is intentional: apply the epoch to complete operations
        # here, rather than letting ORM row filters split a compensating transfer.
        rows = (
            (
                await self.session.execute(
                    daily_flows_query(
                        LedgerTransaction.__table__,
                        start=start,
                        end=end,
                        epoch_started=epoch_started,
                        archive=scope == "archive",
                    )
                )
            )
            .mappings()
            .all()
        )
        by_day = {str(row["day"]): row for row in rows}
        result = []
        for offset in range(days):
            target = first + timedelta(days=offset)
            lo = datetime.combine(target, time.min, MOSCOW).astimezone(UTC)
            hi = lo + timedelta(days=1)
            bounded_lo = (
                max(lo, epoch_started) if epoch_started and scope == "current" else lo
            )
            bounded_hi = (
                min(hi, epoch_started) if epoch_started and scope == "archive" else hi
            )
            raw: Any = by_day.get(target.isoformat(), {})
            item = EconomyDay(
                day=target,
                included=bounded_lo < bounded_hi,
                partial=bounded_lo < bounded_hi
                and (bounded_lo != lo or bounded_hi != hi),
                **{
                    name: int(raw.get(name, 0))
                    for name in (
                        "credited",
                        "debited",
                        "prizes",
                        "refunds",
                        "admin_credit",
                        "admin_debit",
                        "purchases",
                        "issued",
                        "burned",
                        "fund_credited",
                        "fund_debited",
                    )
                },
            )
            result.append(item.payload())
        return {
            "today": today,
            "selected_day": selected,
            "timezone": "Europe/Moscow",
            "epoch": epoch,
            "scope": scope,
            "epoch_started_at": epoch_started,
            "days": result,
        }
