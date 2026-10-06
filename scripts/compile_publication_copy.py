"""Compile the owner's editable libraries into deployable, inert copy data."""

import json
import re
from pathlib import Path


def compile_copy(root: Path) -> None:
    result: dict[str, list[dict[str, str]]] = {}
    for block in ("a", "b"):
        source = (
            root / f"docs/publications/block-{block}/telegram-posts.v1.txt"
        ).read_text(encoding="utf-8")
        for match in re.finditer(
            r"ВАРИАНТ ([AB]\d+-\d+-\d+)\s*\n(.*?)(?=\n[-=]{10,}|\Z)", source, re.S
        ):
            identifier, body = match.groups()
            code = identifier.rsplit("-", 1)[0].replace("-", ".")
            result.setdefault(code, []).append({"id": identifier, "text": body.strip()})
    target = root / "backend/src/k_loto/application/publication_copy.json"
    target.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    compile_copy(Path(__file__).resolve().parents[1])
