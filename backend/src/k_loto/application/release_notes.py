"""Read-only access to versioned project journals for administrators."""

import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

ReleaseNoteKind = Literal["changelog", "devlog"]

_FILES: dict[ReleaseNoteKind, str] = {
    "changelog": "CHANGELOG.md",
    "devlog": "DEVLOG.md",
}
_ENTRY = re.compile(
    r"^## \[([^\]]+)\](?: - (\d{4}-\d{2}-\d{2}))?\s*$",
    flags=re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class ReleaseNote:
    version: str
    date: str | None
    content: str
    sequence: int | None = None


def parse_release_notes(markdown: str) -> tuple[ReleaseNote, ...]:
    """Parse version sections without interpreting or rendering Markdown as HTML."""

    matches = list(_ENTRY.finditer(markdown))
    return tuple(
        ReleaseNote(
            version=match.group(1),
            date=match.group(2),
            content=markdown[
                match.end() : matches[index + 1].start()
                if index + 1 < len(matches)
                else len(markdown)
            ].strip(),
        )
        for index, match in enumerate(matches)
    )


def load_release_notes(
    kind: ReleaseNoteKind, *, project_root: Path | None = None
) -> tuple[ReleaseNote, ...]:
    """Load a journal selected from the fixed allowlist at the project root."""

    root = project_root or Path.cwd()
    notes = parse_release_notes((root / _FILES[kind]).read_text(encoding="utf-8"))
    if kind != "devlog":
        return notes
    total = len(notes)
    return tuple(
        replace(note, sequence=total - index) for index, note in enumerate(notes)
    )
