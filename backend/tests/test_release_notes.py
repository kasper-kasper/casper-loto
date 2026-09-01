"""Tests for the protected project journal read model."""

from pathlib import Path

import pytest

from k_loto.application.release_notes import load_release_notes, parse_release_notes


def test_parser_preserves_all_versioned_sections() -> None:
    notes = parse_release_notes(
        "# Journal\n\nPreamble.\n\n"
        "## [0.2.0] - 2026-08-15\n\n### Added\n\n- Draws.\n\n"
        "## [0.1.0] - 2026-08-14\n\n- Foundation.\n"
    )

    assert [(note.version, note.date) for note in notes] == [
        ("0.2.0", "2026-08-15"),
        ("0.1.0", "2026-08-14"),
    ]
    assert "### Added" in notes[0].content
    assert notes[1].content == "- Foundation."


def test_loader_uses_only_fixed_journal_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "CHANGELOG.md").write_text(
        "## [1.0.0] - 2026-08-31\n\n- Public change.\n", encoding="utf-8"
    )
    (tmp_path / "DEVLOG.md").write_text(
        "## [1.0.0] - 2026-08-31\n\n- Technical change.\n", encoding="utf-8"
    )

    monkeypatch.chdir(tmp_path)
    changelog = load_release_notes("changelog")
    devlog = load_release_notes("devlog")
    assert changelog[0].content == "- Public change."
    assert devlog[0].content == "- Technical change."
    assert changelog[0].sequence is None
    assert devlog[0].sequence == 1


def test_devlog_gets_stable_oldest_first_sequence_without_editing_markdown(
    tmp_path: Path,
) -> None:
    (tmp_path / "DEVLOG.md").write_text(
        "## [1.0.0] - 2026-09-01\n\n- New.\n\n## [0.9.0] - 2026-08-31\n\n- Old.\n",
        encoding="utf-8",
    )

    notes = load_release_notes("devlog", project_root=tmp_path)

    assert [(note.version, note.sequence) for note in notes] == [
        ("1.0.0", 2),
        ("0.9.0", 1),
    ]
