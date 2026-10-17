"""Owner-authorized October economy batch. Intentionally has no resume option."""

import argparse
import asyncio
import json
from datetime import datetime

from k_loto.application.admin import ensure_admin_user
from k_loto.application.economy_transition import EconomyTransitionService
from k_loto.core.config import get_settings
from k_loto.infrastructure.database.session import engine, session_factory


async def run(cutoff: str) -> None:
    timestamp = datetime.fromisoformat(cutoff)
    if timestamp.tzinfo is None:
        raise ValueError("Cutoff must contain a UTC offset.")
    username = get_settings().admin_username
    if not username:
        raise RuntimeError("Configured owner admin identity not found.")
    async with session_factory() as session:
        owner = await ensure_admin_user(session, username)
    async with session_factory() as session:
        result = await EconomyTransitionService(session).activate(
            owner_id=owner, cutoff=timestamp
        )
    print(json.dumps(result))
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cutoff", required=True)
    asyncio.run(run(parser.parse_args().cutoff))
