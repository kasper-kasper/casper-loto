"""Build only published clients from clean source and npm lockfiles."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENTS = ("miniapp", "admin")


def npm_command() -> str:
    installed = shutil.which("npm.cmd") or shutil.which("npm")
    if installed:
        return installed
    portable = next((ROOT / ".tools/node").glob("node-v*-win-x64/npm.cmd"), None)
    if portable:
        return str(portable)
    raise RuntimeError("Node.js/npm is required for the published clients.")


def source_paths(client: str) -> list[str]:
    paths = (
        subprocess.check_output(
            [
                "git",
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "-z",
                f"frontend/{client}",
                "frontend/shared",
            ],
            cwd=ROOT,
        )
        .decode()
        .split("\0")
    )
    return sorted({path for path in paths if path and (ROOT / path).is_file()})


def source_hash(client: str) -> str:
    digest = hashlib.sha256()
    for relative in source_paths(client):
        digest.update(relative.encode() + b"\0")
        digest.update(hashlib.sha256((ROOT / relative).read_bytes()).digest())
    return digest.hexdigest()


def verify_build(client: str) -> None:
    dist = ROOT / "frontend" / client / "dist"
    manifest = json.loads((dist / "build-manifest.json").read_text())
    if manifest["client"] != client or manifest["source_sha256"] != source_hash(client):
        raise RuntimeError(f"{client} artifacts do not match current source.")
    for relative, expected in manifest["files"].items():
        path = dist / relative
        if not path.resolve().is_relative_to(dist.resolve()) or path.is_symlink():
            raise RuntimeError("Out-of-scope build artifact")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Changed {client} artifact: {relative}")


def build(clients: tuple[str, ...] = CLIENTS, *, check: bool = False) -> None:
    npm = npm_command()
    node = str(Path(npm).parent / ("node.exe" if os.name == "nt" else "node"))
    env = {
        **os.environ,
        "PATH": str(Path(npm).parent) + os.pathsep + os.environ.get("PATH", ""),
    }
    # Caller shell overrides must not select a dev API or disable Telegram auth.
    env = {key: value for key, value in env.items() if not key.startswith("VITE_")}
    node_version = subprocess.check_output([node, "--version"], text=True).strip()
    tools = ROOT / ".tools"
    tools.mkdir(exist_ok=True)
    for client in clients:
        if client not in CLIENTS:
            raise ValueError("Only Mini App and Admin are production build targets.")
        before = source_hash(client)
        with tempfile.TemporaryDirectory(
            prefix=f"clean-{client}-", dir=tools
        ) as directory:
            workspace = Path(directory).resolve()
            if not workspace.is_relative_to(tools.resolve()):
                raise RuntimeError("Invalid clean build workspace")
            for relative in source_paths(client):
                target = workspace / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            frontend = workspace / "frontend" / client
            print(f"{client}: clean npm ci", flush=True)
            subprocess.run(
                [npm, "ci", "--no-audit", "--no-fund"],
                cwd=frontend,
                env=env,
                check=True,
            )
            if check:
                for command in ("typecheck", "lint", "test"):
                    args = [npm, "run", command]
                    if command == "test":
                        args += ["--", "--run", "--maxWorkers=2"]
                    subprocess.run(args, cwd=frontend, env=env, check=True)
            subprocess.run([npm, "run", "build"], cwd=frontend, env=env, check=True)
            if source_hash(client) != before:
                raise RuntimeError("Sources changed during the clean build.")
            output = frontend / "dist"
            if not (output / "index.html").is_file():
                raise RuntimeError("Client build is missing index.html.")
            manifest = {
                "client": client,
                "source_sha256": before,
                "node": node_version,
                "lock_sha256": hashlib.sha256(
                    (frontend / "package-lock.json").read_bytes()
                ).hexdigest(),
                "files": {
                    p.relative_to(output).as_posix(): hashlib.sha256(
                        p.read_bytes()
                    ).hexdigest()
                    for p in output.rglob("*")
                    if p.is_file()
                },
            }
            (output / "build-manifest.json").write_text(
                json.dumps(manifest, sort_keys=True), encoding="utf-8"
            )
            destination = ROOT / "frontend" / client / "dist"
            if destination.is_symlink() or not destination.resolve().is_relative_to(
                (ROOT / "frontend" / client).resolve()
            ):
                raise RuntimeError("Invalid generated dist destination")
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(output, destination)
            verify_build(client)
            print(f"{client}: source and artifact hashes verified", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend", nargs="+", choices=CLIENTS, default=list(CLIENTS))
    parser.add_argument("--check", action="store_true")
    options = parser.parse_args()
    build(tuple(options.frontend), check=options.check)
