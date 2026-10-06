"""Focused rules and transport payload checks for the new delivery stage."""

from pathlib import Path

import pytest
from scripts.compile_publication_copy import compile_copy
from sqlalchemy.dialects import postgresql

from k_loto.application.publication_automation import (
    PublicationAutomation,
    caption_html,
    choose,
    format_key,
    publication_eligibility_filter,
    publication_is_eligible,
)


@pytest.mark.parametrize("game", ["flash", "shadow", "pulse"])
@pytest.mark.parametrize("code", ["A2.1", "A2.2", "A2.3", "A3.1", "A3.2"])
async def test_historical_override_never_creates_routine_fast_news(game, code):
    from unittest.mock import AsyncMock

    automation = PublicationAutomation(AsyncMock())
    automation.events._store = AsyncMock()
    assert (
        await automation.store(
            code, "routine", None, None, {}, game=game, historical=True
        )
        is None
    )
    automation.events._store.assert_not_awaited()


@pytest.mark.parametrize("game", ["flash", "shadow", "pulse"])
@pytest.mark.parametrize("code", ["A1.1", "A1.3", "A1.5", "A3.4", "A4.1", "A5.1"])
def test_significant_fast_events_remain_eligible(game, code):
    assert publication_is_eligible(code, game)


def test_ordinary_results_and_platform_events_remain_eligible():
    assert publication_is_eligible("A2.1", "weekly")
    assert publication_is_eligible("B1.2", "casper-loto")
    assert not publication_is_eligible("A2.4", "weekly")
    assert not publication_is_eligible("A1.1", "kasper-live")
    compiled = publication_eligibility_filter().compile(dialect=postgresql.dialect())
    assert ["flash", "shadow", "pulse"] in compiled.params.values()
    assert ["A2.1", "A2.2", "A2.3", "A3.1", "A3.2"] in compiled.params.values()


def test_rotation_excludes_recent_backgrounds_and_falls_back_to_oldest() -> None:
    options = [{"id": key} for key in "abcd"]
    assert choose(options, ["a", "b", "c"], "event")["id"] == "d"
    assert choose(options[:3], ["b", "c", "a"], "event")["id"] == "b"


def test_caption_escapes_owner_copy_and_emits_real_spoiler() -> None:
    assert (
        caption_html("<name> [ПОД СПОЙЛЕРОМ: #лотерея]")
        == "&lt;name&gt; <tg-spoiler>#лотерея</tg-spoiler>"
    )


def test_format_records_survive_price_changes_but_reset_for_rule_changes() -> None:
    snapshot = {
        "ruleset_code": "code",
        "max_number": 9,
        "numbers_to_pick": 5,
        "ticket_price": 10,
    }
    assert format_key(snapshot) == format_key({**snapshot, "ticket_price": 20})
    assert format_key(snapshot) != format_key({**snapshot, "numbers_to_pick": 4})


def test_copy_compiler_has_all_owner_variants(tmp_path: Path) -> None:
    # Compile only into an isolated fixture tree, keeping editable owner text inert.
    import shutil

    root = Path(__file__).resolve().parents[2]
    for block in ("a", "b"):
        target = tmp_path / f"docs/publications/block-{block}"
        target.mkdir(parents=True)
        shutil.copyfile(
            root / f"docs/publications/block-{block}/telegram-posts.v1.txt",
            target / "telegram-posts.v1.txt",
        )
    (tmp_path / "backend/src/k_loto/application").mkdir(parents=True)
    compile_copy(tmp_path)
    import json

    data = json.loads(
        (tmp_path / "backend/src/k_loto/application/publication_copy.json").read_text(
            encoding="utf-8"
        )
    )
    assert sum(len(v) for v in data.values()) == 170
    assert len(data["A1.1"]) == 8 and len(data["B1.1"]) == 5
