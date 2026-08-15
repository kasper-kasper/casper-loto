"""Create or reset a player Web login without exposing secrets."""

import asyncio
from getpass import getpass
from pathlib import Path
from secrets import token_urlsafe

from sqlalchemy import select

from k_loto.infrastructure.database.models import User, WebAccount
from k_loto.infrastructure.database.session import engine, session_factory
from k_loto.infrastructure.web_auth import hash_web_password, normalize_web_username


def set_env_value(lines: list[str], name: str, value: str) -> None:
    prefix = f"{name}="
    for index, line in enumerate(lines):
        if line.strip().upper().startswith(prefix):
            lines[index] = f"{name}={value}"
            return
    lines.append(f"{name}={value}")


async def configure(telegram_id: int, username: str, encoded: str) -> None:
    async with session_factory() as session, session.begin():
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None or user.is_admin:
            raise SystemExit("A regular player with this Telegram ID does not exist.")
        account = await session.scalar(
            select(WebAccount).where(WebAccount.user_id == user.id).with_for_update()
        )
        conflicting = await session.scalar(
            select(WebAccount).where(
                WebAccount.username == username, WebAccount.user_id != user.id
            )
        )
        if conflicting is not None:
            raise SystemExit("This Web username is already in use.")
        if account is None:
            session.add(
                WebAccount(
                    user_id=user.id,
                    username=username,
                    password_hash=encoded,
                    is_active=True,
                )
            )
        else:
            account.username = username
            account.password_hash = encoded
            account.is_active = True


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    env_file = repository_root / ".env"
    if not env_file.exists():
        raise SystemExit("Create .env from .env.example first.")
    try:
        telegram_id = int(input("Existing player Telegram ID: ").strip())
        username = normalize_web_username(input("New Web username: "))
    except ValueError as error:
        raise SystemExit(str(error)) from error
    password = getpass("New Web password: ")
    confirmation = getpass("Repeat password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    encoded = hash_web_password(password)

    lines = env_file.read_text(encoding="utf-8").splitlines()
    existing = next(
        (
            line.partition("=")[2]
            for line in lines
            if line.upper().startswith("WEB_SESSION_SECRET=")
        ),
        "",
    )
    if len(existing) < 32:
        set_env_value(lines, "WEB_SESSION_SECRET", token_urlsafe(48))
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    asyncio.run(configure(telegram_id, username, encoded))
    asyncio.run(engine.dispose())
    print("Web login configured. Password, hash and session secret were not printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
