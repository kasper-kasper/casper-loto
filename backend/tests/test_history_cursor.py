"""History navigation is deterministic, bounded and scoped to one player/filter."""

import base64
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from k_loto.application.ticket_history import (
    TicketHistoryService,
    decode_cursor,
    encode_cursor,
)


def test_history_cursor_roundtrip_preserves_tied_row_identity():
    binding = [str(UUID(int=1)), "", False, "all"]
    key = (datetime(2026, 10, 14, tzinfo=UTC), 123, 1, UUID(int=3))
    assert decode_cursor(encode_cursor(binding, key), binding) == key


@pytest.mark.parametrize(
    "binding",
    [
        [str(UUID(int=2)), "", False, "all"],
        [str(UUID(int=1)), "dual", False, "all"],
        [str(UUID(int=1)), "", True, "all"],
        [str(UUID(int=1)), "", False, "fast"],
    ],
)
def test_history_cursor_cannot_cross_user_or_filter(binding):
    cursor = encode_cursor(
        [str(UUID(int=1)), "", False, "all"], (datetime.now(UTC), 1, 0, UUID(int=3))
    )
    with pytest.raises(ValueError, match="player or filter"):
        decode_cursor(cursor, binding)


@pytest.mark.parametrize("value", ["garbage", "A" * 1025, "W10", "bnVsbA"])
def test_invalid_cursor_is_a_validation_error(value):
    with pytest.raises(ValueError):
        decode_cursor(value, [str(UUID(int=1)), "", False, "all"])


@pytest.mark.parametrize("identifier", [42, [], {}, True])
def test_cursor_with_a_non_string_uuid_is_a_validation_error(identifier):
    binding = [str(UUID(int=1)), "", False, "all"]
    payload = [1, binding, [datetime.now(UTC).isoformat(), 1, 0, identifier]]
    value = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    with pytest.raises(ValueError):
        decode_cursor(value, binding)


async def test_history_rejects_offset_overflow_before_querying_postgres():
    session = AsyncMock()
    with pytest.raises(ValueError):
        await TicketHistoryService(session).page(UUID(int=1), offset=2**63)
    session.execute.assert_not_awaited()
