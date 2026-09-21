"""Live display metadata must come from immutable draw configuration."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from k_loto.api.routes.miniapp import _live_draw_response
from k_loto.application.miniapp import MiniAppQueryService
from k_loto.domain.enums import DrawStatus, LotteryKind
from k_loto.infrastructure.database.models import Draw, Lottery


class EmptyPlayerSession:
    async def execute(self, _statement):
        return self

    def one(self):
        return (0, 0, None, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("snapshot", "offset"),
    [({"ruleset_code": "pulse_2_10_2_5"}, 10), ({}, 12)],
)
async def test_live_format_uses_draw_snapshot(snapshot, offset):
    scheduled = datetime(2026, 9, 21, 12, tzinfo=UTC)
    lottery = Lottery(
        code="pulse",
        name="PULSE",
        kind=LotteryKind.DAILY,
        ruleset_code="pulse_2_12_2_6",
        numbers_to_pick=4,
    )
    draw = Draw(
        id=uuid4(),
        public_number=42,
        scheduled_at=scheduled,
        executed_at=scheduled,
        sales_close_at=scheduled,
        status=DrawStatus.COMPLETED,
        configuration_snapshot=snapshot,
        winning_numbers=[1, 2, offset + 1, offset + 2],
    )
    result = await MiniAppQueryService(EmptyPlayerSession())._live_draw(
        uuid4(), draw, lottery, 10000
    )
    response = _live_draw_response(result)
    assert response.primary_numbers_to_pick == 2
    assert response.secondary_storage_offset == offset
    assert response.winning_numbers == [1, 2, offset + 1, offset + 2]
