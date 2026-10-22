"""Seed a new laptop sandbox using approved terms; never replay a transition."""

import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select

from scripts.local_preview import DATABASE


async def prepare() -> None:
    # Imports occur only after the supervisor supplied isolated local settings.
    from k_loto.application.achievement_catalog import (
        CatalogEntry,
        import_catalog,
        launch_local,
    )
    from k_loto.application.classic_economy import TERMS as CLASSIC
    from k_loto.application.dual_bingo_economy import (
        BingoEconomyService,
        DualEconomyService,
    )
    from k_loto.application.economy_transition import EconomyTransitionService
    from k_loto.application.themed_economy import TERMS as THEMED
    from k_loto.application.weekly import KASPER_FUND_ID
    from k_loto.core.config import get_settings
    from k_loto.domain.enums import LedgerAccountKind
    from k_loto.domain.lottery_rules import CODE_RULES, FAST_RULES, PULSE_RULES
    from k_loto.infrastructure.database.achievement_models import (
        AchievementDefinition,
        AchievementRuntime,
    )
    from k_loto.infrastructure.database.models import (
        Draw,
        JackpotAccount,
        KasperFundAccount,
        Lottery,
        Ticket,
        User,
    )
    from k_loto.infrastructure.database.session import engine, session_factory
    from scripts.local_preview import ROOT

    settings = get_settings()
    if (
        settings.app_env != "development"
        or engine.url.host != "127.0.0.1"
        or engine.url.port != 55439
        or engine.url.database != DATABASE
    ):
        raise RuntimeError("Preview setup requires its exact isolated laptop database.")
    entries = [
        CatalogEntry.model_validate(x)
        for x in json.loads(
            (ROOT / "docs/achievements/achievements.common.catalog.json").read_text(
                encoding="utf-8-sig"
            )
        )
    ]
    from k_loto.application.epic_achievements import epic_catalog
    from k_loto.application.legendary_achievements import legendary_catalog
    from k_loto.application.rare_achievements import rare_catalog
    from k_loto.application.uncommon_achievements import uncommon_catalog

    entries.extend(uncommon_catalog())
    entries.extend(rare_catalog())
    entries.extend(epic_catalog())
    entries.extend(legendary_catalog())
    try:
        async with session_factory() as session, session.begin():
            runtime = await session.get(AchievementRuntime, 1, with_for_update=True)
            assert runtime is not None
            if runtime.started_at is None:
                for model in (User, Draw, Ticket):
                    if await session.scalar(select(func.count()).select_from(model)):
                        raise RuntimeError(
                            "Initial preview setup refuses business history."
                        )
                fund = await session.get(KasperFundAccount, KASPER_FUND_ID)
                assert fund is not None
                terms = (
                    *CLASSIC,
                    *THEMED,
                    *DualEconomyService.terms,
                    *BingoEconomyService.terms,
                    ("flash", FAST_RULES, 2000, 10_000_000),
                    ("shadow", CODE_RULES, 2000, 15_000_000),
                    ("pulse", PULSE_RULES, 2000, 40_000_000),
                )
                for code, rule, price, base in terms:
                    lottery = await session.scalar(
                        select(Lottery).where(Lottery.code == code)
                    )
                    assert lottery is not None
                    jackpot = await session.scalar(
                        select(JackpotAccount).where(
                            JackpotAccount.lottery_id == lottery.id
                        )
                    )
                    assert jackpot is not None
                    movement = EconomyTransitionService(session)
                    delta = base - jackpot.balance
                    if delta:
                        operation = uuid4()
                        for account, kind, amount, suffix in (
                            (fund, LedgerAccountKind.KASPER_FUND, -delta, "fund"),
                            (jackpot, LedgerAccountKind.JACKPOT, delta, "jackpot"),
                        ):
                            movement.move(
                                account,
                                kind,
                                amount,
                                key=f"local-preview:initial:{code}:{suffix}",
                                operation=operation,
                                lottery=lottery.id,
                                step="local-preview-empty-database",
                            )
                    jackpot.base_amount = base
                    lottery.ruleset_code = rule.code
                    lottery.numbers_to_pick = rule.numbers_to_pick
                    lottery.max_number = rule.max_number
                    lottery.ticket_price = price
                    lottery.is_active = True
                    lottery.economy_epoch = 2
                    limit = (
                        600
                        if code in {"weekly", "pss", "khan"}
                        else 50
                        if code == "dual"
                        else 75
                        if code == "bingo"
                        else 500
                        if code in {"flash", "shadow", "pulse"}
                        else 100
                    )
                    lottery.max_tickets_per_user_per_draw = limit
                    lottery.max_tickets_per_purchase = min(
                        limit, 75 if code == "bingo" else 50
                    )
                from k_loto.infrastructure.database.models import EconomyControl

                control = await session.get(EconomyControl, 1)
                assert control is not None and not control.paused
                # Begin fresh schedules now; do not recreate historical empty draws.
                control.recovery_after = datetime.now(UTC)
                await session.flush()
                await import_catalog(session, entries)
                await launch_local(session)
            else:
                existing = {
                    x.code: x
                    for x in (
                        await session.scalars(select(AchievementDefinition))
                    ).all()
                }
                if any(
                    x.code not in existing
                    or any(
                        getattr(existing[x.code], key) != value
                        for key, value in x.model_dump().items()
                    )
                    for x in entries
                ):
                    await import_catalog(session, entries)
        print("Local preview database ready; progress retained.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(prepare())
