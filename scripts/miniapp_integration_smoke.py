"""Real Mini App HTTP + PostgreSQL checks on synthetic audit data only."""

import asyncio
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from uuid import uuid4

import httpx
from sqlalchemy import func, select, text

from k_loto.application.scheduler import DrawScheduleService
from k_loto.application.weekly import LotterySettlementService, _ledger_entry
from k_loto.core.config import Settings, get_settings
from k_loto.domain.enums import DrawStatus, LedgerAccountKind, TransactionType
from k_loto.infrastructure.admin_auth import password_hash
from k_loto.infrastructure.database.models import (
    Draw,
    KasperFundAccount,
    Lottery,
)
from k_loto.infrastructure.database.session import engine, session_factory
from k_loto.main import create_app


def init_data(token, telegram_id):
    values = {
        "auth_date": str(int(datetime.now(UTC).timestamp())),
        "query_id": uuid4().hex,
        "user": json.dumps(
            {"id": telegram_id, "first_name": "Synthetic integration"},
            separators=(",", ":"),
        ),
    }
    data = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, data.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def ticket_ids(result):
    return result.get("ticket_ids") or [item["id"] for item in result["tickets"]]


async def main():
    if not str(engine.url.database).startswith("k_loto_audit_stage1_"):
        raise RuntimeError("Disposable audit database required")
    config = Settings(
        database_url=get_settings().database_url,
        app_env="test",
        web_enabled=False,
        lottery_bot_token="999999:synthetic-only",
        scheduler_enabled=False,
        admin_username="synthetic-owner",
        admin_secret="s" * 48,
        admin_password_hash=password_hash.hash("synthetic-test-password"),
        miniapp_purchase_requests_per_minute=120,
    )
    now = datetime.now(UTC)
    async with session_factory() as session, session.begin():
        fund = await session.scalar(select(KasperFundAccount).with_for_update())
        before = fund.balance
        fund.balance += 10**15
        fund.version += 1
        session.add(
            _ledger_entry(
                operation_id=uuid4(),
                idempotency_key="integration:fund",
                account_kind=LedgerAccountKind.KASPER_FUND,
                account_id=fund.id,
                transaction_type=TransactionType.SYSTEM_ADJUSTMENT,
                before=before,
                after=fund.balance,
            )
        )
        weekly = await session.scalar(
            select(Lottery).where(Lottery.code == "audit-weekly").with_for_update()
        )
        weekly.is_active = True
        number = (
            int(
                await session.scalar(
                    select(func.max(Draw.public_number)).where(
                        Draw.lottery_id == weekly.id
                    )
                )
                or 0
            )
            + 1
        )
        draw = Draw(
            id=uuid4(),
            lottery_id=weekly.id,
            public_number=number,
            status=DrawStatus.SCHEDULED,
            scheduled_at=now + timedelta(hours=1),
            sales_close_at=now + timedelta(minutes=55),
            correlation_id=uuid4(),
        )
        session.add(draw)
        weekly.next_draw_number = number + 1
        dual = await session.scalar(
            select(Lottery).where(Lottery.code == "dual").with_for_update()
        )
        dual.is_active = True
        first_at = now.replace(hour=21, minute=30, second=0, microsecond=0) + timedelta(
            days=2
        )
        number = (
            int(
                await session.scalar(
                    select(func.max(Draw.public_number)).where(
                        Draw.lottery_id == dual.id
                    )
                )
                or 0
            )
            + 1
        )
        for offset, at in enumerate((first_at, first_at + timedelta(hours=7))):
            session.add(
                Draw(
                    id=uuid4(),
                    lottery_id=dual.id,
                    public_number=number + offset,
                    status=DrawStatus.SCHEDULED,
                    scheduled_at=at,
                    sales_close_at=at - timedelta(minutes=2),
                    correlation_id=uuid4(),
                )
            )
        dual.next_draw_number = number + 2
        bingo = await session.scalar(select(Lottery).where(Lottery.code == "bingo"))
        bingo.is_active = True
        bingo_id = bingo.id
    async with session_factory() as session:
        bingo_draw, _ = await DrawScheduleService(session).ensure_next_draw(
            bingo_id, reference=now
        )
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: config
    headers = {
        "X-Telegram-Init-Data": init_data(
            config.lottery_bot_token.get_secret_value(), 8_000_000_000_101
        )
    }
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=application), base_url="http://localhost"
    ) as client:
        assert (await client.get("/api/v1/miniapp/account")).status_code == 401
        assert (
            await client.get(
                "/api/v1/miniapp/account", headers={"X-Telegram-Init-Data": "tampered"}
            )
        ).status_code == 401
        assert (await client.get("/api/v1/web/session")).status_code == 404
        assert (await client.get("/api/v1/admin/monitoring")).status_code == 401
        login = await client.post(
            "/api/v1/admin/auth/login",
            json={"username": "synthetic-owner", "password": "synthetic-test-password"},
        )
        assert login.status_code == 200
        assert (await client.get("/api/v1/admin/monitoring")).status_code == 200
        assert (
            await client.get("/api/v1/miniapp/account", headers=headers)
        ).status_code == 200
        generic = "/api/v1/miniapp/lotteries/audit-weekly/purchases"
        requests = [
            (
                generic,
                "scheduled",
                {
                    "combinations": [[1, 2, 3, 4, 5]],
                    "expected_scheduled_at": draw.scheduled_at.isoformat(),
                },
            ),
            (
                "/api/v1/miniapp/lotteries/dual/purchases",
                "scheduled",
                {
                    "combinations": [[1, 2, 13, 14]],
                    "expected_scheduled_at": first_at.isoformat(),
                },
            ),
            (
                "/api/v1/miniapp/bingo/purchases",
                "scheduled",
                {"draw_id": str(bingo_draw.id), "quantity": 1},
            ),
            *[
                (f"/api/v1/miniapp/{game}/purchases", game, {"quantity": 1})
                for game in ("kasper-live", "aurora", "vault")
            ],
        ]
        for index, (path, game, payload) in enumerate(requests):
            key = f"m1-integration-{index}"
            body = {**payload, "idempotency_key": key}
            first = await client.post(path, headers=headers, json=body)
            assert first.status_code == 201, first.text
            replay = await client.post(path, headers=headers, json=body)
            assert replay.status_code == 201, replay.text
            assert ticket_ids(first.json()) == ticket_ids(replay.json())
            assert replay.json()["already_processed"]
            receipt_path = f"/api/v1/miniapp/purchase-receipts/{key}?game={game}"
            receipt = (await client.get(receipt_path, headers=headers)).json()[
                "receipt"
            ]
            assert ticket_ids(receipt) == ticket_ids(first.json())
            cancelled = (
                await client.post(
                    receipt_path.replace("?", "/cancel?"), headers=headers
                )
            ).json()
            assert not cancelled["cancelled"] and ticket_ids(
                cancelled["receipt"]
            ) == ticket_ids(receipt)
            unseen = f"m1-integration-cancel-{index}"
            cancelled = await client.post(
                f"/api/v1/miniapp/purchase-receipts/{unseen}/cancel?game={game}",
                headers=headers,
            )
            assert cancelled.json()["cancelled"]
            assert (
                await client.post(
                    path, headers=headers, json={**payload, "idempotency_key": unseen}
                )
            ).status_code == 422
        wrong = await client.post(
            generic,
            headers=headers,
            json={
                "combinations": [[1, 2, 3, 4, 5]],
                "expected_scheduled_at": (
                    draw.scheduled_at + timedelta(hours=1)
                ).isoformat(),
                "idempotency_key": "m1-cutoff-mismatch",
            },
        )
        assert wrong.status_code == 409
        bad_favorite = await client.post(
            "/api/v1/miniapp/lotteries/audit-weekly/favorites",
            headers=headers,
            json={"numbers": [999]},
        )
        assert bad_favorite.status_code == 422
        batch = await client.post(
            generic,
            headers=headers,
            json={
                "combinations": [[1, 2, 3, 8, 9]] * 80,
                "idempotency_key": "m1-history-fixture",
                "expected_scheduled_at": draw.scheduled_at.isoformat(),
            },
        )
        assert batch.status_code == 201, batch.text

        class FixedNumbers:
            def draw(self, population_size, numbers_to_pick):
                return (1, 2, 3, 4, 5)

        async with session_factory() as session:
            await LotterySettlementService(session, FixedNumbers()).settle(
                draw.id, now=draw.scheduled_at
            )
        async with session_factory() as session:
            before_history = await session.scalar(
                text(
                    "SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) "
                    "FROM tickets t"
                )
            )
        seen = []
        cursor = None
        first_cursor = None
        for _ in range(100):
            params = {"state": "history", "scope": "all", "limit": "7"}
            if cursor:
                params["cursor"] = cursor
            response = await client.get(
                "/api/v1/miniapp/tickets", headers=headers, params=params
            )
            assert response.status_code == 200, response.text
            page = response.json()
            assert len(page["tickets"]) <= 7
            for item in page["tickets"]:
                if item["lottery_code"] == "audit-weekly":
                    assert item["draw_ticket_count"] == 81
            seen.extend(item["id"] for item in page["tickets"])
            cursor = page["next_cursor"]
            first_cursor = first_cursor or cursor
            if not page["has_more"]:
                break
        else:
            raise AssertionError("History cursor failed to terminate")
        assert len(seen) == len(set(seen)) == page["total"] == 84
        for params in (
            {"state": "history", "cursor": first_cursor, "wins_only": "true"},
            {"state": "history", "cursor": "invalid"},
        ):
            assert (
                await client.get(
                    "/api/v1/miniapp/tickets", headers=headers, params=params
                )
            ).status_code == 422
        other = {
            "X-Telegram-Init-Data": init_data(
                config.lottery_bot_token.get_secret_value(), 8_000_000_000_102
            )
        }
        assert (
            await client.get(
                "/api/v1/miniapp/tickets",
                headers=other,
                params={"state": "history", "cursor": first_cursor},
            )
        ).status_code == 422
        assert (
            await client.get(
                "/api/v1/miniapp/purchase-receipts/m1-integration-0", headers=other
            )
        ).json()["receipt"] is None
        account = (await client.get("/api/v1/miniapp/account", headers=headers)).json()
        assert account["favorite_numbers"] == [1, 2, 3, 8, 9, 4, 5]
        for game in ("kasper-live", "aurora", "vault"):
            page = (
                await client.get(
                    "/api/v1/miniapp/tickets",
                    headers=headers,
                    params={"state": "history", "lottery_code": game},
                )
            ).json()
            assert page["total"] == 1 and page["tickets"][0]["lottery_code"] == game
        async with session_factory() as session:
            assert (
                await session.scalar(
                    text(
                        "SELECT md5(string_agg(row_to_json(t)::text,'' ORDER BY id)) "
                        "FROM tickets t"
                    )
                )
                == before_history
            )
        print(
            "Mini App HTTP/PostgreSQL: auth, monitoring, "
            "six purchase/replay/receipt/cancel paths, cutoff, favorites, "
            "stable mixed history and privacy PASS"
        )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
