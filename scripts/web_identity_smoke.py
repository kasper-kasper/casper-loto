"""Exercise browser identity against an explicitly disposable PostgreSQL DB."""

import asyncio
from uuid import uuid4

from sqlalchemy import func, select

from k_loto.application.identity import TelegramIdentityService
from k_loto.application.web_identity import WebIdentityError, WebIdentityService
from k_loto.core.config import get_settings
from k_loto.infrastructure.database.base import Base
from k_loto.infrastructure.database.models import Balance, LedgerTransaction, User
from k_loto.infrastructure.database.session import engine, session_factory


async def main() -> None:
    if not str(get_settings().database_url).endswith("/k_loto_web_smoke"):
        raise RuntimeError("Only the disposable k_loto_web_smoke database is allowed.")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        profile = await TelegramIdentityService(session).bind(
            telegram_id=777777777, username="smoke", display_name="Smoke"
        )
        service = WebIdentityService(session)
        code = await service.issue_telegram_code(profile.id)

    async def redeem() -> bool:
        async with session_factory() as session:
            try:
                user = await WebIdentityService(session).redeem_telegram_code(code)
                assert user.id == profile.id
                return True
            except WebIdentityError:
                return False

    assert sorted(await asyncio.gather(redeem(), redeem())) == [False, True]
    async with session_factory() as session:
        service = WebIdentityService(session)
        await service.add_password(profile.id, "smoke-player", "test-only-password")
        assert await session.scalar(select(func.count()).select_from(User)) == 1
        assert (
            await session.scalar(select(func.count()).select_from(LedgerTransaction))
            == 1
        )
        assert (
            await session.scalar(
                select(Balance.amount).where(Balance.user_id == profile.id)
            )
            == profile.balance
        )
        await session.rollback()
        account, user = await service.register(
            "separate-" + uuid4().hex[:8], "test-password"
        )
        assert account.user_id == user.id and user.id != profile.id
    print(
        "PASS: concurrent code redemption exactly once; shared UUID and balance; "
        "no duplicate grant; password registration."
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
