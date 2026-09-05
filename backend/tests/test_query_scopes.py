"""Read queries must separate frequent Fast activity before pagination."""

from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.admin import AdminQueryService
from k_loto.application.miniapp import MiniAppQueryService
from k_loto.application.query_scope import LotteryScope


class EmptyResult:
    def all(self) -> list[Any]:
        return []

    def first(self) -> None:
        return None


class RecordingSession:
    def __init__(self) -> None:
        self.sql: list[str] = []

    def record(self, statement: Any) -> None:
        self.sql.append(
            str(
                statement.compile(
                    dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
                )
            )
        )

    async def execute(self, statement: Any) -> EmptyResult:
        self.record(statement)
        return EmptyResult()

    async def scalar(self, statement: Any) -> int:
        self.record(statement)
        return 0


@pytest.mark.asyncio
@pytest.mark.parametrize("scope, operator", [("standard", "NOT IN"), ("fast", " IN")])
async def test_ticket_page_and_total_use_the_same_scope(
    scope: LotteryScope, operator: str
) -> None:
    session = RecordingSession()
    service = MiniAppQueryService(cast(AsyncSession, session))
    await service.tickets(UUID(int=1), active=False, scope=scope, limit=10, offset=20)
    await service.ticket_count(UUID(int=1), active=False, scope=scope)
    for sql in session.sql:
        assert operator in sql
        assert all(code in sql for code in ("flash", "shadow", "pulse"))
        assert "tickets.user_id =" in sql
    assert session.sql[0].index(operator) < session.sql[0].index("LIMIT 10")
    assert "OFFSET 20" in session.sql[0]


@pytest.mark.asyncio
async def test_latest_jackpot_and_nearest_draw_exclude_fast_before_limit() -> None:
    session = RecordingSession()
    result = await MiniAppQueryService(cast(AsyncSession, session)).highlights(
        UUID(int=1)
    )
    assert result == {"last_jackpot": None, "next_event": None}
    assert len(session.sql) == 2
    for sql in session.sql:
        assert sql.index("NOT IN") < sql.index("LIMIT 1")


@pytest.mark.asyncio
async def test_admin_fast_history_is_filtered_before_pagination() -> None:
    session = RecordingSession()
    await AdminQueryService(cast(AsyncSession, session), scope="fast").draws(
        period="completed", limit=100, offset=100
    )
    sql = session.sql[0]
    assert "lotteries.code IN" in sql
    assert "draws.status = 'COMPLETED'" in sql
    assert "LIMIT 100 OFFSET 100" in sql


@pytest.mark.asyncio
async def test_live_room_queries_only_its_lottery() -> None:
    session = RecordingSession()
    await MiniAppQueryService(cast(AsyncSession, session)).live(
        UUID(int=1), lottery_code="khan"
    )
    assert len(session.sql) == 2
    assert all("lotteries.code = 'khan'" in sql for sql in session.sql)
