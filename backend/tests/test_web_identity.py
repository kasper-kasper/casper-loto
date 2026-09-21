"""One-time Telegram access must reuse identity and never issue CAS."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.application.web_identity import WebIdentityError, WebIdentityService
from k_loto.infrastructure.database.models import User, WebAccount, WebLoginToken
from k_loto.infrastructure.web_auth import issue_web_session, validate_web_session


class Transaction:
    async def __aenter__(self) -> None:
        pass

    async def __aexit__(self, *_args: object) -> None:
        pass


class FakeSession:
    def __init__(self, values: list[Any]) -> None:
        self.values = iter(values)
        self.added: list[Any] = []
        self.statements: list[Any] = []

    def begin(self) -> Transaction:
        return Transaction()

    async def scalar(self, statement: Any) -> Any:
        self.statements.append(statement)
        return next(self.values)

    async def execute(self, statement: Any) -> None:
        self.statements.append(statement)

    def add(self, item: Any) -> None:
        self.added.append(item)


def player() -> User:
    return User(
        id=uuid4(),
        telegram_id=42,
        display_name="Player",
        is_active=True,
        is_admin=False,
    )


async def test_code_is_hashed_short_lived_and_replaces_previous_codes() -> None:
    user = player()
    session = FakeSession([user])
    code = await WebIdentityService(cast(AsyncSession, session)).issue_telegram_code(
        user.id
    )
    token = session.added[0]
    assert len(code) == 16
    assert isinstance(token, WebLoginToken)
    assert token.user_id == user.id
    assert token.token_hash != code and len(token.token_hash) == 64
    assert (
        datetime.now(UTC) < token.expires_at <= datetime.now(UTC) + timedelta(minutes=5)
    )
    assert "UPDATE web_login_tokens" in str(session.statements[1])


async def test_redeem_preserves_identity_and_consumes_under_lock() -> None:
    user = player()
    token = WebLoginToken(
        user_id=user.id, expires_at=datetime.now(UTC) + timedelta(minutes=1)
    )
    session = FakeSession([token, user, token])
    service = WebIdentityService(cast(AsyncSession, session))
    result = await service.redeem_telegram_code("A" * 16)
    assert result.id == user.id
    assert token.used_at is not None
    assert "FOR UPDATE" in str(session.statements[0])
    assert session.added == []  # no User, Balance, grant or ledger write
    with pytest.raises(WebIdentityError):
        await service.redeem_telegram_code("A" * 16)


@pytest.mark.parametrize("expired,used", [(True, False), (False, True)])
async def test_invalid_codes_are_rejected(expired: bool, used: bool) -> None:
    now = datetime.now(UTC)
    token = WebLoginToken(
        expires_at=now + timedelta(seconds=-1 if expired else 60),
        used_at=now if used else None,
    )
    service = WebIdentityService(cast(AsyncSession, FakeSession([token])))
    with pytest.raises(WebIdentityError):
        await service.redeem_telegram_code("B" * 16)


async def test_password_is_added_to_same_user_without_new_balance() -> None:
    user = player()
    session = FakeSession([user, None])
    await WebIdentityService(cast(AsyncSession, session)).add_password(
        user.id, "Player.Name", "long-password"
    )
    assert len(session.added) == 1
    account = session.added[0]
    assert isinstance(account, WebAccount)
    assert account.user_id == user.id
    assert account.username == "player.name"
    assert account.password_hash != "long-password"


def test_telegram_session_is_signed_and_retains_canonical_id() -> None:
    user_id = uuid4()
    token, _ = issue_web_session(None, user_id, "a" * 40)
    session = validate_web_session(token, "a" * 40)
    assert session.account_id is None
    assert session.user_id == user_id
