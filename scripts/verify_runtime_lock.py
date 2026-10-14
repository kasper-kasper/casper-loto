"""Check the installed application/dependencies against the committed uv lock."""

import argparse
import hashlib
import json
import sys
import tomllib
from importlib.metadata import distributions
from pathlib import Path

from k_loto import __version__


def manifest(*, allow_dev: bool = False) -> dict:
    root = Path(__file__).resolve().parents[1]
    lock_bytes = (root / "uv.lock").read_bytes()
    lock = tomllib.loads(lock_bytes.decode())
    versions: dict[str, set[str]] = {}
    for package in lock["package"]:
        versions.setdefault(package["name"].lower().replace("_", "-"), set()).add(
            package["version"]
        )
    installed = {
        item.metadata["Name"].lower().replace("_", "-"): item.version
        for item in distributions()
    }
    for name, version in installed.items():
        if version not in versions.get(name, set()):
            raise RuntimeError(
                f"Runtime distribution is outside uv.lock: {name} {version}"
            )
    project = next(p for p in lock["package"] if p["name"] == "k-loto")
    if installed.get("k-loto") != __version__ or project["version"] != __version__:
        raise RuntimeError("Application and package versions disagree")
    for dependency in project["dependencies"]:
        if dependency["name"] not in installed:
            raise RuntimeError(f"Missing application dependency: {dependency['name']}")
    if not allow_dev and any(
        name in installed for name in ("pytest", "mypy", "ruff", "paramiko")
    ):
        raise RuntimeError("Production runtime contains development tools")
    return {
        "application": __version__,
        "python": sys.version.split()[0],
        "uv_lock_sha256": hashlib.sha256(lock_bytes).hexdigest(),
        "packages": installed,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path)
    parser.add_argument("--allow-dev", action="store_true")
    options = parser.parse_args()
    result = manifest(allow_dev=options.allow_dev)
    if options.write:
        options.write.write_text(json.dumps(result, sort_keys=True))
    print(
        f"Runtime {result['application']}: "
        f"{len(result['packages'])} locked distributions verified"
    )
