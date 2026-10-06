"""Focused rules and transport payload checks for the new delivery stage."""

from pathlib import Path

import pytest
from scripts.compile_publication_copy import compile_copy
from sqlalchemy.dialects import postgresql

from k_loto.application.publication_automation import (
    PublicationAutomation,
    caption_html,
    choose,
    editorial_snapshot,
    format_key,
    jackpot_record_eligible,
    publication_eligibility_filter,
    publication_is_eligible,
    unique_winners_record_eligible,
)


@pytest.mark.parametrize(
    "game", ["flash", "shadow", "pulse", "weekly", "dual", "september"]
)
@pytest.mark.parametrize(
    "code", ["A2.1", "A2.2", "A2.3", "A3.1", "A3.2", "A4.3", "A5.2"]
)
async def test_historical_override_never_creates_unqualified_news(game, code):
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
@pytest.mark.parametrize("code", ["A1.1", "A1.3", "A1.5", "A4.1"])
def test_significant_fast_events_remain_eligible(game, code):
    assert publication_is_eligible(
        code, game, {"new_record": 200000000, "previous_record": 100000000}
    )


@pytest.mark.parametrize(
    "increase,accepted",
    [(2000000, False), (99999999, False), (100000000, True), (150000000, True)],
)
def test_jackpot_record_minimum_gap(increase, accepted):
    assert jackpot_record_eligible(599000000 + increase, 599000000) == accepted
    for code in ("A1.3", "A1.4", "B2.1"):
        assert (
            publication_is_eligible(
                code,
                "weekly",
                {
                    "new_record": 599000000 + increase,
                    "previous_record": 599000000 + increase - 1000,
                    "publication_baseline": 599000000,
                },
            )
            == accepted
        )
        assert not publication_is_eligible(
            code, "weekly", {"new_record": 599000000, "previous_record": 597000000}
        )


def test_routine_results_blocked_and_platform_events_remain_eligible():
    assert not publication_is_eligible("A2.1", "weekly")
    assert publication_is_eligible("B1.2", "casper-loto")
    assert not publication_is_eligible("A2.4", "weekly")
    assert not publication_is_eligible("A1.1", "kasper-live")
    compiled = publication_eligibility_filter().compile(dialect=postgresql.dialect())
    assert ["flash", "shadow", "pulse"] in compiled.params.values()
    assert ["A2.1", "A2.2", "A2.3", "A3.1", "A3.2"] in compiled.params.values()


@pytest.mark.parametrize(
    "current,previous,eligible",
    [(20, 0, False), (21, 0, True), (21, 21, False), (22, 23, False), (25, 21, True)],
)
def test_unique_winner_record_requires_more_than_twenty_and_a_new_maximum(
    current, previous, eligible
):
    assert unique_winners_record_eligible(current, previous) == eligible
    assert (
        publication_is_eligible(
            "A5.5",
            "dual",
            {
                "metric": "unique_winners_per_draw",
                "new_record": current,
                "previous_record": previous,
            },
        )
        == eligible
    )
    assert not publication_is_eligible("A5.5", "dual", {"value": current})


def test_participant_records_are_absent_from_manual_catalog():
    from k_loto.application.publications import template_catalog

    assert not any(t["subcategory"] in {"A4.3", "A5.2"} for t in template_catalog())


def test_fast_catalog_contains_only_owner_backgrounds():
    from k_loto.application.publications import template_catalog

    fast = [
        t for t in template_catalog() if t["lottery"] in {"flash", "shadow", "pulse"}
    ]
    assert fast and all(t["id"].startswith("fast-owner-v1-") for t in fast)


def test_pending_publications_lose_service_footer_and_old_fast_artwork():
    content = {
        "channel_caption": "Новость\n\nСобытие: 06.10.2026 10:00 МСК",
        "event": {"type": "A4.1"},
        "fields": {"fact": "06.10.2026 10:00 МСК"},
        "template": {"id": "old-flash", "subcategory": "A4.1"},
    }
    result = editorial_snapshot(content, "flash")
    assert result["channel_caption"] == "Новость"
    assert result["fields"]["fact"] == ""
    assert result["template"]["id"].startswith("fast-owner-v1-")
    assert content["template"]["id"] == "old-flash"


def test_meaningful_jackpot_date_is_preserved_in_copy():
    content = {"channel_caption": "Джекпот сорван 5 октября", "event": {"type": "A1.1"}}
    assert (
        editorial_snapshot(content, "weekly")["channel_caption"]
        == content["channel_caption"]
    )


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
