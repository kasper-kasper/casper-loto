"""Verify public HTTPS, exact deployed clients and retirement of browser APIs."""

import hashlib
import json
import re
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def fetch(url: str, expected: int = 200) -> bytes:
    for attempt in range(5):
        try:
            request = Request(url, headers={"Cache-Control": "no-cache"})
            try:
                with urlopen(request, timeout=15) as response:
                    status, data = response.status, response.read()
            except HTTPError as error:
                status, data = error.code, error.read()
            if status != expected:
                raise RuntimeError(
                    f"Unexpected HTTPS status {status}; expected {expected}"
                )
            return data
        except (OSError, RuntimeError):
            if attempt == 4:
                raise
            time.sleep(2)
    raise AssertionError("Unreachable")


def main() -> None:
    config = {}
    for line in (ROOT / ".env.production").read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            config[key.strip()] = value.strip().strip('"').strip("'")
    for name, frontend in (("WEB_HOST", "miniapp"), ("ADMIN_HOST", "admin")):
        host = config[name]
        base = host.rstrip("/") if host.startswith("https://") else f"https://{host}"
        health = json.loads(fetch(base + "/health"))
        assert health["status"] == "ok" and health["database"]["status"] == "ok"
        local = (ROOT / "frontend" / frontend / "dist" / "index.html").read_bytes()
        remote = fetch(base + "/")
        assert hashlib.sha256(local).digest() == hashlib.sha256(remote).digest()
        for asset in re.findall(r'(?:src|href)="(/assets/[^\"]+)"', local.decode()):
            data = fetch(base + asset)
            expected = (
                ROOT / "frontend" / frontend / "dist" / asset.lstrip("/")
            ).read_bytes()
            assert hashlib.sha256(data).digest() == hashlib.sha256(expected).digest()
        fetch(base + "/api/v1/web/auth/session", 404)
        if frontend == "miniapp":
            fetch(base + "/web", 410)
            fetch(base + "/web/", 410)
            pause = json.loads(fetch(base + "/api/v1/miniapp/maintenance"))
            fetch(
                base + "/api/v1/miniapp/dashboard", 503 if pause["maintenance"] else 401
            )
        else:
            fetch(base + "/api/v1/admin/auth/session", 401)
        print(
            f"{frontend}: public HTTPS, exact HTML, auth boundary "
            "and web API retirement OK"
        )
    assert not (ROOT / "frontend" / "web").exists()


if __name__ == "__main__":
    main()
