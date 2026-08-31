"""Telegram Mini App authentication and transport tests."""

import hmac
import json
from datetime import UTC, datetime
from hashlib import sha256
from urllib.parse import urlencode

import pytest
from pydantic import ValidationError

from k_loto.api.routes.miniapp import PurchaseRequest, _live_response
from k_loto.application.miniapp import (
    MiniAppLiveDraw,
    MiniAppLiveFeed,
    MiniAppLiveTicket,
)
from k_loto.domain.enums import DrawStatus, LotteryKind
from k_loto.infrastructure.telegram_auth import (
    InvalidTelegramInitData,
    validate_init_data,
)
from k_loto.main import create_app


def signed_init_data(
    *,
    bot_token: str,
    auth_date: int,
    user: dict[str, object] | None = None,
) -> str:
    values = {
        "auth_date": str(auth_date),
        "query_id": "AAE-test-query",
        "user": json.dumps(
            user
            or {
                "id": 123456,
                "first_name": "K",
                "last_name": "Loto",
                "username": "player",
            },
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(values.items())
    )
    secret = hmac.new(b"WebAppData", bot_token.encode(), sha256).digest()
    values["hash"] = hmac.new(secret, data_check_string.encode(), sha256).hexdigest()
    return urlencode(values)


def test_valid_init_data_returns_authenticated_telegram_user() -> None:
    now = datetime(2026, 8, 14, 12, tzinfo=UTC)
    init_data = signed_init_data(
        bot_token="test-bot-token", auth_date=int(now.timestamp())
    )

    user = validate_init_data(init_data, "test-bot-token", now=now)

    assert user.telegram_id == 123456
    assert user.username == "player"
    assert user.display_name == "K Loto"


def test_tampered_init_data_is_rejected() -> None:
    now = datetime(2026, 8, 14, 12, tzinfo=UTC)
    init_data = signed_init_data(
        bot_token="test-bot-token", auth_date=int(now.timestamp())
    ).replace("player", "attacker")

    with pytest.raises(InvalidTelegramInitData, match="signature"):
        validate_init_data(init_data, "test-bot-token", now=now)


def test_missing_init_data_is_rejected() -> None:
    with pytest.raises(InvalidTelegramInitData, match="missing"):
        validate_init_data("", "test-bot-token")


def test_expired_init_data_is_rejected() -> None:
    now = datetime(2026, 8, 14, 12, tzinfo=UTC)
    init_data = signed_init_data(
        bot_token="test-bot-token", auth_date=int(now.timestamp()) - 3601
    )

    with pytest.raises(InvalidTelegramInitData, match="expired"):
        validate_init_data(init_data, "test-bot-token", now=now)


def test_future_init_data_is_rejected() -> None:
    now = datetime(2026, 8, 14, 12, tzinfo=UTC)
    init_data = signed_init_data(
        bot_token="test-bot-token", auth_date=int(now.timestamp()) + 31
    )

    with pytest.raises(InvalidTelegramInitData, match="future"):
        validate_init_data(init_data, "test-bot-token", now=now)


def test_miniapp_routes_are_registered() -> None:
    paths = create_app().openapi()["paths"]

    assert "/api/v1/miniapp/dashboard" in paths
    assert "/api/v1/miniapp/live" in paths
    assert "/api/v1/miniapp/tickets" in paths
    assert "/api/v1/miniapp/weekly/purchases" in paths
    assert "/api/v1/miniapp/daily/purchases" in paths
    assert "/api/v1/miniapp/lotteries/{lottery_code}/purchases" in paths
    assert "/api/v1/miniapp/dev/session" in paths
    assert "/api/v1/miniapp/dev/refill" in paths


def test_live_response_exposes_server_clock_and_personal_result() -> None:
    scheduled = datetime(2026, 8, 31, 9, tzinfo=UTC)
    draw = MiniAppLiveDraw(
        lottery_code="pss",
        lottery_name="ПСС-Лото",
        lottery_kind=LotteryKind.DAILY,
        draw_number=812,
        scheduled_at=scheduled,
        status=DrawStatus.COMPLETED,
        winning_numbers=(2, 5, 9, 14),
        jackpot=24_000_000,
        player_ticket_count=2,
        player_winning_ticket_count=1,
        player_best_matches=3,
        player_total_prize=120_000,
        highlighted_tickets=(MiniAppLiveTicket(50465, (2, 5, 9, 11), 3, 120_000),),
    )

    response = _live_response(MiniAppLiveFeed(scheduled, draw, None, (draw,)))

    assert response.server_time == scheduled
    assert response.latest_completed is not None
    assert response.latest_completed.winning_numbers == [2, 5, 9, 14]
    assert response.latest_completed.player_total_prize == 120_000
    assert response.latest_completed.highlighted_tickets[0].public_number == 50465
    assert response.recent_completed[0].draw_number == 812


def test_miniapp_rejects_more_than_one_hundred_tickets_per_request() -> None:
    with pytest.raises(ValidationError):
        PurchaseRequest(
            combinations=[[1, 2, 3, 4, 5]] * 101,
            idempotency_key="too-many",
        )
