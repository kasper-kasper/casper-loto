"""Bingo rules: immutable rows, first closing moves and integer prize shares."""

import secrets
from dataclasses import dataclass
from uuid import UUID

from k_loto.domain.errors import InvalidTicket

BINGO_CODE = "bingo_12_60"
BINGO_ECONOMY_CODE = "bingo_12_60_economy_v2"
POOL_SIZE = 2000
DRAW_MOVES = 58
JACKPOT_MOVE = 28
TOUR_PRIZES = (100_000, 500_000)
TOUR_MOVES = (18, 34)
FIXED_TOUR_PRIZES = (50_000, 100_000, 20_000)
FIXED_TOUR_MOVES = (18, 34, 58)
KASPER_SET_NUMBERS = (2, 9, 16, 28)
KASPER_SET_SIZE = 10
KASPER_SET_INVENTORY = 100


def stage_cutoffs(ruleset_code: str) -> tuple[int, ...]:
    # Keep the historical jackpot slot (index 2); append the new full-card tour.
    return (
        (*TOUR_MOVES, JACKPOT_MOVE, DRAW_MOVES)
        if ruleset_code == BINGO_ECONOMY_CODE
        else (*TOUR_MOVES, JACKPOT_MOVE)
    )


def public_rules(ruleset_code: str) -> dict[str, object]:
    fixed = ruleset_code == BINGO_ECONOMY_CODE
    return {
        "total_moves": DRAW_MOVES,
        "jackpot_move": JACKPOT_MOVE,
        "tour_moves": list(FIXED_TOUR_MOVES if fixed else TOUR_MOVES),
        "tour_prizes": list(FIXED_TOUR_PRIZES if fixed else TOUR_PRIZES),
        "stage_moves": list(stage_cutoffs(ruleset_code)),
        "fixed_per_card": fixed,
        "pool_size": POOL_SIZE,
    }


def validate_ticket(numbers: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    if (
        len(numbers) != 12
        or len(set(numbers)) != 12
        or any(type(n) is not int or not 1 <= n <= 60 for n in numbers)
    ):
        raise InvalidTicket("Bingo requires 12 unique integers from 1 to 60.")
    return tuple(numbers)


def generate_ticket() -> tuple[int, ...]:
    numbers = secrets.SystemRandom().sample(range(1, 61), 12)
    return tuple(n for i in range(0, 12, 4) for n in sorted(numbers[i : i + 4]))


def generate_sequence() -> tuple[int, ...]:
    return tuple(secrets.SystemRandom().sample(range(1, 61), DRAW_MOVES))


def closing_moves(
    numbers: tuple[int, ...], sequence: tuple[int, ...]
) -> tuple[int, ...]:
    validate_ticket(numbers)
    positions = {n: i + 1 for i, n in enumerate(sequence)}
    return tuple(
        sorted(
            max(positions.get(n, 61) for n in numbers[i : i + 4])
            for i in range(0, 12, 4)
        )
    )


@dataclass(frozen=True)
class BingoOutcome:
    moves: tuple[int, ...]
    amounts: tuple[int, ...]


def outcomes(
    tickets: list[tuple[UUID, int, tuple[int, ...]]],
    sequence: tuple[int, ...],
    jackpot: int,
    *,
    fixed_per_card: bool = False,
) -> dict[UUID, BingoOutcome]:
    if (
        len(sequence) != DRAW_MOVES
        or len(set(sequence)) != DRAW_MOVES
        or any(type(n) is not int or not 1 <= n <= 60 for n in sequence)
    ):
        raise InvalidTicket("Bingo draw must be an ordered permutation of 1–60.")
    moves = {tid: closing_moves(numbers, sequence) for tid, _, numbers in tickets}
    amounts = {tid: [0] * (4 if fixed_per_card else 3) for tid, _, _ in tickets}
    cutoffs = stage_cutoffs(BINGO_ECONOMY_CODE if fixed_per_card else BINGO_CODE)
    prizes = (
        (FIXED_TOUR_PRIZES[0], FIXED_TOUR_PRIZES[1], jackpot, FIXED_TOUR_PRIZES[2])
        if fixed_per_card
        else (*TOUR_PRIZES, jackpot)
    )
    for category, (pool, cutoff) in enumerate(zip(prizes, cutoffs, strict=True)):
        winners = sorted(
            (serial, tid)
            for tid, serial, _ in tickets
            if moves[tid][min(category, 2)] <= cutoff
        )
        if not winners:
            continue
        share, remainder = (
            (pool, 0)
            if fixed_per_card and category != 2
            else divmod(pool, len(winners))
        )
        for index, (_, tid) in enumerate(winners):
            amounts[tid][category] = share + int(index < remainder)
    return {tid: BingoOutcome(moves[tid], tuple(amounts[tid])) for tid in moves}
