"""Archive pagination, immutable result projection and transport regressions."""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.draw_archive import DrawArchiveService, archive_draw
from k_loto.domain.enums import DrawStatus
from k_loto.infrastructure.database.models import Draw, Lottery
from k_loto.main import create_app


def result_row(number: int = 1, code: str = "khan") -> tuple[Draw, Lottery, int]:
    return (
        Draw(
            id=UUID(int=number),
            public_number=number,
            scheduled_at=datetime(2026, 10, 4, tzinfo=UTC),
            status=DrawStatus.COMPLETED,
            total_payout=12345,
            ticket_count=8,
            winning_numbers=[1, 2, 3, 4, 5, 6],
            configuration_snapshot={},
        ),
        Lottery(code=code, name=code, ruleset_code="classic_6_36"),
        10000,
    )


class Result:
    def __init__(self, rows: list[Any]) -> None:
        self.rows = rows

    def all(self) -> list[Any]:
        return self.rows

    def first(self) -> Any:
        return self.rows[0] if self.rows else None


class Session:
    def __init__(self, results: list[list[Any]]) -> None:
        self.results = results
        self.sql: list[str] = []

    async def execute(self, statement: Any) -> Result:
        self.sql.append(
            str(
                statement.compile(
                    dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
                )
            )
        )
        return Result(self.results.pop(0))


async def test_bounded_page_excludes_fast_before_pagination_and_uses_events() -> None:
    session = Session(
        [[result_row(3), result_row(2), result_row(1)], [("khan", "6 из 36")]]
    )
    page = await DrawArchiveService(cast(AsyncSession, session)).page(
        lottery_code="khan",
        jackpots_only=True,
        limit=2,
    )
    assert [item.draw_number for item in page.items] == [3, 2]
    assert page.next_cursor == UUID(int=2)
    sql = session.sql[0]
    assert "draws.status = 'COMPLETED'" in sql
    assert "lotteries.code = 'khan'" in sql
    assert "jackpot_win_events.id IS NOT NULL" in sql
    assert sql.index("NOT IN") < sql.index("LIMIT 3")
    assert all(code in sql for code in ("flash", "shadow", "pulse"))
    assert "ORDER BY draws.scheduled_at DESC, draws.id DESC" in sql
    assert "JOIN tickets" not in sql and "OFFSET" not in sql
    assert "NOT IN" in session.sql[1]


async def test_cursor_uses_stable_date_and_id_and_ends_at_first_draw() -> None:
    date = datetime(2026, 10, 4, tzinfo=UTC)
    session = Session([[(date, UUID(int=2))], [result_row(1)], []])
    page = await DrawArchiveService(cast(AsyncSession, session)).page(
        before=UUID(int=2)
    )
    assert page.next_cursor is None
    assert page.items[0].draw_number == 1
    assert "(draws.scheduled_at, draws.id) <" in session.sql[1]
    assert "LIMIT 31" in session.sql[1]


async def test_missing_cursor_is_rejected() -> None:
    session = Session([[]])
    with pytest.raises(ValueError):
        await DrawArchiveService(cast(AsyncSession, session)).page(before=UUID(int=1))


def test_bingo_omits_large_sequence_and_count_but_preserves_payout_and_jackpot() -> (
    None
):
    draw, lottery, jackpot = result_row(code="bingo")
    item = archive_draw(draw, lottery, jackpot)
    assert item.winning_numbers is None and item.ticket_count is None
    assert item.total_payout == 12345 and item.jackpot_amount == 10000
    assert draw.winning_numbers == [1, 2, 3, 4, 5, 6]


def test_historical_format_comes_from_draw_snapshot() -> None:
    draw, lottery, _ = result_row()
    draw.configuration_snapshot = {"ruleset_code": "weekly_grand_5_35_2_5"}
    item = archive_draw(draw, lottery, None)
    assert item.secondary_storage_offset == 35
    assert item.jackpot_amount is None


def test_archive_requires_miniapp_authentication() -> None:
    client = TestClient(create_app())
    assert client.get("/api/v1/miniapp/draw-archive").status_code == 401
