"""Final-release application of prepared economy batches; never reopens the app."""

import asyncio
import json

from k_loto.application.admin import ensure_admin_user
from k_loto.application.classic_economy import ClassicEconomyService
from k_loto.application.themed_economy import ThemedEconomyService
from k_loto.core.config import get_settings
from k_loto.infrastructure.database.session import engine, session_factory


async def run() -> None:
    username = get_settings().admin_username
    if not username:
        raise RuntimeError("Configured owner admin identity not found.")
    async with session_factory() as session:
        owner = await ensure_admin_user(session, username)
    results = {}
    for service in (ThemedEconomyService, ClassicEconomyService):
        async with session_factory() as session:
            results[service.step] = await service(session).apply(owner_id=owner)
    print(json.dumps(results))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
