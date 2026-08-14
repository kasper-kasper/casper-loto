"""FastAPI dependencies shared by transport handlers."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from k_loto.infrastructure.database.session import session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield one database session per request."""
    async with session_factory() as session:
        yield session
