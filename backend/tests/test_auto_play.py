"""Auto-play orchestration regressions."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from k_loto.application import auto_play as auto_play_module
from k_loto.application.auto_play import (
    AutoPlayCandidate,
    AutoPlayService,
    auto_play_error_code,
)
from k_loto.domain.enums import LotteryKind, TicketSource
from k_loto.domain.errors import (
    ConfigurationError,
    InsufficientBalance,
    InvalidTicket,
    NoAvailableDraw,
)
from k_loto.domain.lottery_rules import DUAL_RULES, WEEKLY_RULES
from k_loto.infrastructure import scheduler as scheduler_module


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (InsufficientBalance(), "INSUFFICIENT_BALANCE"),
        (NoAvailableDraw(), "SALES_CLOSED"),
        (InvalidTicket("ticket limit reached"), "TICKET_LIMIT_REACHED"),
        (InvalidTicket("bad numbers"), "INVALID_COMBINATION"),
        (ConfigurationError(), "TECHNICAL_ERROR"),
    ],
)
def test_auto_play_errors_have_stable_owner_facing_reasons(
    error: Exception, code: str
) -> None:
    assert auto_play_error_code(error) == code


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


async def test_auto_play_excludes_dual_and_limits_other_games_to_five_draws() -> None:
    draw_ids = [UUID(int=value) for value in range(1, 8)]
    setting = SimpleNamespace(user_id=UUID(int=20), tickets_per_draw=5)
    lottery = SimpleNamespace(
        code="weekly", kind=LotteryKind.WEEKLY, ruleset_code=WEEKLY_RULES.code
    )
    dual = SimpleNamespace(
        code="dual", kind=LotteryKind.DAILY, ruleset_code=DUAL_RULES.code
    )

    class Rows:
        def __init__(self, values: list[Any]) -> None:
            self.values = values

        def all(self) -> list[Any]:
            return self.values

    class Session(FakeSession):
        call_count = 0

        async def execute(self, _query: object) -> Rows:
            self.call_count += 1
            if self.call_count == 1:
                return Rows([(draw_id, UUID(int=30)) for draw_id in draw_ids])
            return Rows(
                [
                    (
                        setting,
                        SimpleNamespace(id=draw_id, configuration_snapshot={}),
                        lottery,
                    )
                    for draw_id in draw_ids
                ]
                + [
                    (
                        setting,
                        SimpleNamespace(id=UUID(int=40), configuration_snapshot={}),
                        dual,
                    )
                ]
            )

    service = AutoPlayService(lambda: Session())  # type: ignore[arg-type]
    candidates = await service._candidates(datetime(2026, 9, 25, tzinfo=UTC))

    assert [candidate.draw_id for candidate in candidates] == draw_ids[:5]
    assert all(candidate.tickets_per_draw == 5 for candidate in candidates)


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


async def test_scheduler_runs_auto_play_without_owner_only_filter(
    monkeypatch: Any,
) -> None:
    constructor_kwargs: list[dict[str, Any]] = []

    class FakeHeartbeat:
        last_failed_at = None
        last_error = None
        last_succeeded_at = None
        settled_count = 0
        prepared_count = 0

    class FakeRuntimeSession(FakeSession):
        def begin(self) -> "FakeRuntimeSession":
            return self

        async def execute(self, _query: object) -> None:
            return None

        async def get(self, _model: object, _key: object) -> FakeHeartbeat:
            return FakeHeartbeat()

    class FakeRecovery:
        async def reconcile(self, *, now: datetime) -> Any:
            return type(
                "Report", (), {"settled_draw_ids": (), "prepared_draw_ids": ()}
            )()

    class FakeAutoPlay:
        def __init__(self, _factory: object, **kwargs: Any) -> None:
            constructor_kwargs.append(kwargs)

        async def run(self, *, now: datetime) -> None:
            return None

    class FakeEngagement:
        def __init__(self, _factory: object) -> None:
            pass

        async def run(self, *, now: datetime) -> None:
            return None

    class FakeMonitor:
        async def run(self, *, now: datetime) -> None:
            return None

    monkeypatch.setattr(
        scheduler_module, "session_factory", lambda: FakeRuntimeSession()
    )
    monkeypatch.setattr(scheduler_module, "AutoPlayService", FakeAutoPlay)
    monkeypatch.setattr(scheduler_module, "PlayerEngagementService", FakeEngagement)
    runtime = scheduler_module.SchedulerRuntime(10)
    runtime._recovery = FakeRecovery()  # type: ignore[assignment]
    runtime._monitor = FakeMonitor()  # type: ignore[assignment]

    await runtime._run()

    assert constructor_kwargs == [{}]
