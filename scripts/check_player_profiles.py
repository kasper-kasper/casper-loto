"""Read-only projection verification, or an explicit derived-data rebuild."""

import argparse
import asyncio
from dataclasses import asdict

from sqlalchemy import text

from k_loto.application.profile_projection import ProfileProjectionService
from k_loto.infrastructure.database.session import engine, session_factory


async def main(rebuild: bool = False) -> None:
    try:
        async with session_factory() as session, session.begin():
            if rebuild:
                await ProfileProjectionService(session).rebuild()
            else:
                await session.execute(text("SET TRANSACTION READ ONLY"))
            check = await ProfileProjectionService(session).verify()
            print(asdict(check))
            if check.profiles or check.lotteries:
                raise RuntimeError("Player display projection differs from history")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true")
    asyncio.run(main(parser.parse_args().rebuild))
