"""Activate owner-approved Grand rules during a stopped-service release."""

import asyncio
import json
from dataclasses import asdict
from uuid import uuid5

from sqlalchemy import select

from k_loto.application.admin import ADMIN_NAMESPACE
from k_loto.application.lottery_transition import LotteryFormatTransitionService
from k_loto.application.scheduler import DrawRecoveryService
from k_loto.core.config import get_settings
from k_loto.domain.lottery_rules import GRAND_FIXED_RULES, KASPER_GRAND_RULES
from k_loto.infrastructure.database.models import User
from k_loto.infrastructure.database.session import engine, session_factory


async def main() -> None:
    admin_username = get_settings().admin_username
    if not admin_username:
        raise RuntimeError("Configured administrative audit actor is required.")
    # Use the existing Admin Panel credential's stable audit identity, exactly
    # as ensure_admin_user does, without granting or changing any user rights.
    admin_id = uuid5(ADMIN_NAMESPACE, admin_username.casefold())
    # Preserve and chronologically settle overdue old-format draws first.
    await DrawRecoveryService(session_factory).reconcile()
    async with session_factory() as session:
        owner_id = await session.scalar(
            select(User.id).where(User.id == admin_id, User.is_admin.is_(True))
        )
    if owner_id is None:
        raise RuntimeError("Configured owner account is missing or not admin.")
    async with session_factory() as session:
        result = await LotteryFormatTransitionService(
            session,
            lottery_code="weekly",
            source_rules=KASPER_GRAND_RULES,
            target_rules=GRAND_FIXED_RULES,
            ticket_price=50_000,
            namespace="grand-fixed-v1",
        ).activate(owner_id=owner_id)
    print(json.dumps(asdict(result), sort_keys=True))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
