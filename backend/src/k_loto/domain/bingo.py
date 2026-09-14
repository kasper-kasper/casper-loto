"""Bingo rules: immutable rows, first closing moves and integer prize shares."""

import secrets
from dataclasses import dataclass
from uuid import UUID

from k_loto.domain.errors import InvalidTicket

BINGO_CODE = "bingo_12_60"
POOL_SIZE = 2000
DRAW_MOVES = 58
JACKPOT_MOVE = 28
TOUR_PRIZES = (100_000, 500_000)
TOUR_MOVES = (18, 34)
KASPER_SET_NUMBERS = (2, 9, 16, 28)
KASPER_SET_SIZE = 10
KASPER_SET_INVENTORY = 100


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
) -> dict[UUID, BingoOutcome]:
    if (
        len(sequence) != DRAW_MOVES
        or len(set(sequence)) != DRAW_MOVES
        or any(type(n) is not int or not 1 <= n <= 60 for n in sequence)
    ):
        raise InvalidTicket("Bingo draw must be an ordered permutation of 1–60.")
    moves = {tid: closing_moves(numbers, sequence) for tid, _, numbers in tickets}
    amounts = {tid: [0, 0, 0] for tid, _, _ in tickets}
    cutoffs = (*TOUR_MOVES, JACKPOT_MOVE)
    for category, (pool, cutoff) in enumerate(
        zip((*TOUR_PRIZES, jackpot), cutoffs, strict=True)
    ):
        winners = sorted(
            (serial, tid)
            for tid, serial, _ in tickets
            if moves[tid][category] <= cutoff
        )
        if not winners:
            continue
        share, remainder = divmod(pool, len(winners))
        for index, (_, tid) in enumerate(winners):
            amounts[tid][category] = share + int(index < remainder)
    return {tid: BingoOutcome(moves[tid], tuple(amounts[tid])) for tid in moves}
