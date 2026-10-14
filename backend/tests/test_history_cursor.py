"""History navigation is deterministic, bounded and scoped to one player/filter."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from k_loto.application.ticket_history import decode_cursor, encode_cursor


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
