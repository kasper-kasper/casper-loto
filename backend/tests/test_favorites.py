"""Reusable favorite-combination rules."""

import pytest

from k_loto.application.favorites import validate_favorite_numbers


def test_favorite_numbers_are_normalized_for_daily_and_weekly() -> None:
    assert validate_favorite_numbers(
        (15, 1, 7, 4), numbers_to_pick=4, max_number=15
    ) == (1, 4, 7, 15)
    assert validate_favorite_numbers(
        (20, 1, 12, 5, 7), numbers_to_pick=5, max_number=20
    ) == (1, 5, 7, 12, 20)


@pytest.mark.parametrize(
    "numbers",
    [(1, 2, 3), (1, 2, 3, 3), (0, 2, 3, 4), (1, 2, 3, 16)],
)
def test_invalid_daily_favorite_is_rejected(numbers: tuple[int, ...]) -> None:
    with pytest.raises(ValueError):
        validate_favorite_numbers(numbers, numbers_to_pick=4, max_number=15)
