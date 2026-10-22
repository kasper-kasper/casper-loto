"""Approved October payouts, burn split and maintenance boundaries."""

from datetime import UTC, datetime, timedelta
from itertools import combinations
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from k_loto.application.economy import schedule_checkpoint
from k_loto.domain.draw_state import ensure_draw_transition
from k_loto.domain.enums import DrawStatus
from k_loto.domain.errors import InvalidStateTransition
from k_loto.domain.lottery_rules import (
    CODE_RULES,
    FAST_RULES,
    PULSE_RULES,
    SettlementTicket,
)


def payout(rule, numbers, winning):
    ticket = SettlementTicket(uuid4(), 1, uuid4(), tuple(numbers), 2_000)
    plan = rule.calculate_settlement(
        [ticket],
        winning,
        distribution_balance=0,
        jackpot_balance=40_000_000,
        reserve_balance=100_000_000,
        base_jackpot=40_000_000,
    )
    assert len(plan.payouts) == 1
    return plan.payouts[0].amount


@pytest.mark.parametrize(
    "rule,numbers",
    [
        (FAST_RULES, [1, 2, 3, 4, 5]),
        (CODE_RULES, [0, 0, 0, 0, 0]),
        (PULSE_RULES, [1, 2, 13, 14, 1001]),
    ],
)
def test_per_ticket_burn_is_independent_of_bulk_size(rule, numbers):
    for count in (1, 25, 100):
        quote = rule.quote_purchase([numbers] * count, 2_000, 2_000 * count)
        assert quote.jackpot_contribution == 800 * count
        assert quote.total_cost - quote.jackpot_contribution == 1_200 * count


def test_flash_all_categories_and_single_highest_prize():
    for matches, amount in enumerate([0, 0, 2_000, 8_000, 100_000, 40_000_000]):
        assert (
            payout(
                FAST_RULES,
                [*range(1, matches + 1), *range(10, 15 - matches)],
                [1, 2, 3, 4, 5],
            )
            == amount
        )


def test_code_all_exact_position_categories():
    for matches, amount in enumerate([0, 2_000, 4_000, 10_000, 500_000, 40_000_000]):
        assert (
            payout(CODE_RULES, [0] * matches + [1] * (5 - matches), [0] * 5) == amount
        )


def test_pulse_every_combination_and_both_cipher_outcomes():
    expected = {
        (1, 1): 4000,
        (0, 2): 4000,
        (1, 2): 8000,
        (2, 0): 14000,
        (2, 1): 14000,
        (2, 2): 500_000,
    }
    total = jackpot_count = 0
    for primary in combinations(range(1, 13), 2):
        for secondary in combinations(range(13, 19), 2):
            a, b = len(set(primary) & {1, 2}), len(set(secondary) & {13, 14})
            total += 1
            for cipher in (1001, 1002):
                amount = (
                    40_000_000
                    if (a, b, cipher) == (2, 2, 1001)
                    else expected.get((a, b), 0)
                )
                assert (
                    payout(
                        PULSE_RULES,
                        [*primary, *secondary, cipher],
                        [1, 2, 13, 14, 1001],
                    )
                    == amount
                )
            jackpot_count += int((a, b) == (2, 2))
    assert total * PULSE_RULES.server_code_max // jackpot_count == 197_010


def test_cancelled_slots_are_terminal_and_resume_skips_only_planned_time():
    ensure_draw_transition(DrawStatus.SCHEDULED, DrawStatus.CANCELLED)
    for target in DrawStatus:
        with pytest.raises(InvalidStateTransition):
            ensure_draw_transition(DrawStatus.CANCELLED, target)
    resume = datetime(2026, 10, 18, 12, tzinfo=UTC)
    control = SimpleNamespace(recovery_after=resume)
    assert schedule_checkpoint(resume - timedelta(hours=6), control) == resume
    assert schedule_checkpoint(
        resume + timedelta(hours=1), control
    ) == resume + timedelta(hours=1)


def test_public_pause_gate_runs_before_authentication(monkeypatch):
    from k_loto.api import economy_maintenance
    from k_loto.main import create_app

    async def paused(_session):
        return True

    monkeypatch.setattr(economy_maintenance, "is_paused", paused)
    client = TestClient(create_app())
    assert client.get("/api/v1/miniapp/maintenance").json()["maintenance"] is True
    for path in ("dashboard", "lotteries/flash/purchases", "profile"):
        response = client.post(f"/api/v1/miniapp/{path}")
        assert response.status_code == 503
        assert response.json()["maintenance"] is True
    assert (
        client.post(
            "/api/v1/admin/players/anything", headers={"X-Economy-Scope": "archive"}
        ).status_code
        == 403
    )


def test_open_status_does_not_announce_economy_maintenance(monkeypatch):
    from k_loto.api import economy_maintenance
    from k_loto.main import create_app

    async def paused(_session):
        return False

    monkeypatch.setattr(economy_maintenance, "is_paused", paused)
    response = TestClient(create_app()).get("/api/v1/miniapp/maintenance")
    assert response.json() == {"maintenance": False, "message": None}
    assert response.headers["cache-control"] == "no-store"
