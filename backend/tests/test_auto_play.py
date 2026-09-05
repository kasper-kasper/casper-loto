"""Auto-play orchestration regressions."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from k_loto.application import auto_play as auto_play_module
from k_loto.application.auto_play import AutoPlayCandidate, AutoPlayService
from k_loto.domain.enums import LotteryKind, TicketSource


class FixedGenerator:
    def draw(self, population_size: int, numbers_to_pick: int) -> tuple[int, ...]:
        assert (population_size, numbers_to_pick) == (20, 5)
        return (1, 2, 3, 4, 5)

    def draw_sequence(self, minimum: int, maximum: int, length: int) -> tuple[int, ...]:
        assert (minimum, maximum, length) == (0, 9, 4)
        return (0, 0, 7, 3)


class FakeSession:
    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


class AutoPlayHarness(AutoPlayService):
    def __init__(self, candidate: AutoPlayCandidate) -> None:
        super().__init__(lambda: FakeSession(), FixedGenerator())  # type: ignore[arg-type]
        self.candidate = candidate
        self.attempts: list[tuple[UUID, str | None]] = []

    async def _candidates(self, now: datetime) -> tuple[AutoPlayCandidate, ...]:
        return (self.candidate,)

    async def _record_attempt(
        self, user_id: UUID, now: datetime, error: str | None
    ) -> None:
        self.attempts.append((user_id, error))


async def test_auto_play_buys_five_random_tickets_with_stable_idempotency(
    monkeypatch: Any,
) -> None:
    calls: list[dict[str, Any]] = []

    class FakePurchaseService:
        def __init__(
            self, _session: object, lottery_code: str, *, target_draw_id: UUID
        ) -> None:
            assert lottery_code == "weekly"
            assert target_draw_id == UUID(int=2)

        async def purchase(self, **kwargs: Any) -> None:
            calls.append(kwargs)

    monkeypatch.setattr(
        auto_play_module, "LotteryTicketPurchaseService", FakePurchaseService
    )
    candidate = AutoPlayCandidate(
        user_id=UUID(int=1),
        draw_id=UUID(int=2),
        lottery_code="weekly",
        lottery_kind=LotteryKind.WEEKLY,
        numbers_to_pick=5,
        max_number=20,
        tickets_per_draw=5,
    )
    service = AutoPlayHarness(candidate)
    now = datetime(2026, 9, 1, 12, tzinfo=UTC)

    report = await service.run(now=now)

    assert report.purchased_draw_ids == (candidate.draw_id,)
    assert report.failed_draw_ids == ()
    assert calls[0]["combinations"] == [[1, 2, 3, 4, 5]] * 5
    assert calls[0]["source"] == TicketSource.AUTO_PLAY
    assert calls[0]["idempotency_key"] == (
        f"auto:{candidate.user_id.hex}:{candidate.draw_id.hex}:weekly_5_20"
    )
    assert service.attempts == [(candidate.user_id, None)]


async def test_auto_play_uses_new_ruleset_key_after_format_refund(
    monkeypatch: Any,
) -> None:
    calls: list[dict[str, Any]] = []

    class FakePurchaseService:
        def __init__(
            self, _session: object, lottery_code: str, *, target_draw_id: UUID
        ) -> None:
            assert lottery_code == "shadow"

        async def purchase(self, **kwargs: Any) -> None:
            calls.append(kwargs)

    monkeypatch.setattr(
        auto_play_module, "LotteryTicketPurchaseService", FakePurchaseService
    )
    candidate = AutoPlayCandidate(
        user_id=UUID(int=11),
        draw_id=UUID(int=12),
        lottery_code="shadow",
        lottery_kind=LotteryKind.DAILY,
        numbers_to_pick=4,
        max_number=9,
        tickets_per_draw=1,
        ruleset_code="code_4_digits",
    )

    await AutoPlayHarness(candidate).run(now=datetime(2026, 9, 5, 12, tzinfo=UTC))

    assert calls[0]["combinations"] == [[0, 0, 7, 3]]
    assert calls[0]["idempotency_key"].endswith(":code_4_digits")
