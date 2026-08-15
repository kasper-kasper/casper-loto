"""Configure local administrator credentials without printing secrets."""

from getpass import getpass
from pathlib import Path
from secrets import token_urlsafe

from pwdlib import PasswordHash


def set_env_value(lines: list[str], name: str, value: str) -> None:
    prefix = f"{name}="
    for index, line in enumerate(lines):
        if line.strip().upper().startswith(prefix):
            lines[index] = f"{name}={value}"
            return
    lines.append(f"{name}={value}")


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    env_file = repository_root / ".env"
    if not env_file.exists():
        raise SystemExit("Create .env from .env.example first.")
    username = input("Administrator username: ").strip()
    if not username or len(username) > 128:
        raise SystemExit("Username must contain 1 to 128 characters.")
    password = getpass("Administrator password: ")
    confirmation = getpass("Repeat password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters.")

    lines = env_file.read_text(encoding="utf-8").splitlines()
    set_env_value(lines, "ADMIN_USERNAME", username)
    set_env_value(
        lines, "ADMIN_PASSWORD_HASH", PasswordHash.recommended().hash(password)
    )
    set_env_value(lines, "ADMIN_SECRET", token_urlsafe(48))
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Administrator credentials were saved to ignored .env.")
    print("The password, hash and session secret were not printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
