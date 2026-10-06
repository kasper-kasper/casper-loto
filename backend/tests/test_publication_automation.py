"""Focused rules and transport payload checks for the new delivery stage."""

from pathlib import Path

from scripts.compile_publication_copy import compile_copy

from k_loto.application.publication_automation import caption_html, choose, format_key


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
