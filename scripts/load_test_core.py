"""Repeatable in-memory load probe for bulk purchase validation and settlement."""

from __future__ import annotations

import argparse
from time import perf_counter
from uuid import UUID

from k_loto.domain.daily import calculate_daily_settlement, quote_daily_purchase
from k_loto.domain.weekly import SettlementTicket, calculate_weekly_settlement


def run(ticket_count: int) -> None:
    daily_combinations = [
        [1 + index % 12, 2 + index % 12, 3 + index % 12, 4 + index % 12]
        for index in range(ticket_count)
    ]
    started = perf_counter()
    quote = quote_daily_purchase(daily_combinations, 24_000, 10**15)
    purchase_seconds = perf_counter() - started

    tickets = [
        SettlementTicket(
            id=UUID(int=index + 1),
            public_number=index + 1,
            user_id=UUID(int=(index % 100) + 1),
            numbers=tuple(daily_combinations[index]),
            purchase_price=24_000,
        )
        for index in range(ticket_count)
    ]
    started = perf_counter()
    daily = calculate_daily_settlement(
        tickets,
        (1, 2, 3, 4),
        distribution_balance=10**15,
        jackpot_balance=24_000_000,
        reserve_balance=10**15,
        base_jackpot=24_000_000,
    )
    daily_seconds = perf_counter() - started

    weekly_tickets = [
        SettlementTicket(
            id=UUID(int=index + 1),
            public_number=index + 1,
            user_id=UUID(int=(index % 100) + 1),
            numbers=(1, 2, 3, 4, 5),
            purchase_price=100,
        )
        for index in range(ticket_count)
    ]
    started = perf_counter()
    weekly = calculate_weekly_settlement(
        weekly_tickets,
        (1, 2, 3, 6, 7),
        distribution_balance=10**15,
        jackpot_balance=10**9,
        reserve_balance=10**15,
        base_jackpot=10**6,
    )
    weekly_seconds = perf_counter() - started

    assert len(quote.combinations) == ticket_count
    assert len(daily.payouts) == ticket_count
    assert len(weekly.payouts) == ticket_count
    print(f"tickets={ticket_count}")
    print(f"bulk_purchase_validation_seconds={purchase_seconds:.4f}")
    print(f"daily_settlement_seconds={daily_seconds:.4f}")
    print(f"weekly_settlement_seconds={weekly_seconds:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickets", type=int, default=5_000)
    arguments = parser.parse_args()
    if arguments.tickets < 1:
        parser.error("--tickets must be positive")
    run(arguments.tickets)
