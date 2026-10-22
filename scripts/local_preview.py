"""One-click Windows preview with isolated settings and persistent local data."""

import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".tools/local-preview"
DATABASE = "k_loto_achievement_preview"
CONTAINER = "k-loto-achievements-local"
URL = "http://127.0.0.1:5173"
API = "http://127.0.0.1:8000"


def isolated_environment(secret: str) -> dict[str, str]:
    # Deliberately exclude all inherited application settings and credentials.
    allowed = {
        "SYSTEMROOT",
        "WINDIR",
        "PATH",
        "PATHEXT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "COMSPEC",
        "HOMEDRIVE",
        "HOMEPATH",
    }
    env = {k: v for k, v in os.environ.items() if k.upper() in allowed}
    env.update(
        {
            "PYTHONPATH": os.pathsep.join((str(ROOT), str(ROOT / "backend/src"))),
            "PYTHONUTF8": "1",
            "APP_ENV": "development",
            "DATABASE_URL": f"postgresql+asyncpg://postgres@127.0.0.1:55439/{DATABASE}",
            "MINIAPP_DEV_AUTH_ENABLED": "true",
            "MINIAPP_DEV_USER_TELEGRAM_ID": "900000002",
            "MINIAPP_DEV_SESSION_SECRET": secret,
            "MINIAPP_DEV_INITIAL_BALANCE": "1000000",
            "SCHEDULER_ENABLED": "true",
            "ACHIEVEMENTS_WORKER_ENABLED": "true",
            "ACHIEVEMENTS_NOTIFICATIONS_ENABLED": "false",
            "EDITORIAL_ENABLED": "false",
            "OWNER_DAILY_SUMMARY_ENABLED": "false",
            "WEB_ENABLED": "false",
            "LOG_LEVEL": "WARNING",
            "MONITORING_BACKUP_DIR": str(RUNTIME / "backups"),
            "VITE_LOCAL_DEV_AUTH": "true",
            "VITE_DESIGN_PREVIEW": "false",
            "VITE_API_BASE_URL": "",
            "BROWSER": "none",
        }
    )
    return env


def run(args: list[str], *, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        args,
        cwd=RUNTIME,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    with (RUNTIME / "setup.log").open("a", encoding="utf-8") as log:
        log.write(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("Setup failed. See .tools/local-preview/setup.log")
    return result.stdout.strip()


def ensure_database() -> None:
    docker = shutil.which("docker")
    if not docker:
        raise RuntimeError("Docker Desktop is not installed or not on PATH.")

    def docker_ready() -> bool:
        try:
            return (
                subprocess.run(
                    [docker, "info", "--format", "{{.ServerVersion}}"],
                    capture_output=True,
                    timeout=4,
                ).returncode
                == 0
            )
        except subprocess.TimeoutExpired:
            return False

    if not docker_ready():
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "Programs/DockerDesktop/Docker Desktop.exe",
            Path(os.environ.get("PROGRAMFILES", "C:/Program Files"))
            / "Docker/Docker/Docker Desktop.exe",
        ]
        executable = next((p for p in candidates if p.is_file()), None)
        if executable is None:
            raise RuntimeError("Start Docker Desktop and try again.")
        print("Starting Docker Desktop; please wait...", flush=True)
        subprocess.Popen([str(executable)], creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + 150
        while not docker_ready():
            if time.monotonic() > deadline:
                raise RuntimeError("Docker is not ready. Start it and try again.")
            time.sleep(2)
    names = run([docker, "container", "ls", "-a", "--format", "{{.Names}}"])
    if CONTAINER not in names.splitlines():
        run(
            [
                docker,
                "run",
                "-d",
                "--name",
                CONTAINER,
                "-p",
                "127.0.0.1:55439:5432",
                "-e",
                "POSTGRES_HOST_AUTH_METHOD=trust",
                "-v",
                "k-loto-local-preview-data:/var/lib/postgresql/data",
                "postgres:16-alpine",
            ]
        )
    ports = json.loads(
        run(
            [
                docker,
                "inspect",
                "--format",
                "{{json .HostConfig.PortBindings}}",
                CONTAINER,
            ]
        )
    )
    if ports != {"5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "55439"}]}:
        raise RuntimeError("Local database must be bound only to 127.0.0.1:55439.")
    if (
        run([docker, "inspect", "--format", "{{.Config.Image}}", CONTAINER])
        != "postgres:16-alpine"
    ):
        raise RuntimeError("Unexpected local database container image.")
    run([docker, "start", CONTAINER])
    for _ in range(45):
        check = subprocess.run(
            [docker, "exec", CONTAINER, "pg_isready", "-U", "postgres"],
            capture_output=True,
            timeout=5,
        )
        if check.returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError("Local PostgreSQL is not ready.")
    exists = run(
        [
            docker,
            "exec",
            CONTAINER,
            "psql",
            "-U",
            "postgres",
            "-d",
            "postgres",
            "-Atc",
            f"SELECT 1 FROM pg_database WHERE datname='{DATABASE}'",
        ]
    )
    if exists != "1":
        run([docker, "exec", CONTAINER, "createdb", "-U", "postgres", DATABASE])


def claim_instance():
    import msvcrt

    handle = (RUNTIME / "running.lock").open("a+b")
    # Reading another instance's locked byte is itself denied on Windows.
    if os.fstat(handle.fileno()).st_size == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close()
        return None
    return handle


def windows_process_job():
    """Closing the console also terminates its API and Vite children."""
    import ctypes
    from ctypes import wintypes

    class Limits(ctypes.Structure):
        _fields_ = [
            ("process_time", ctypes.c_int64),
            ("job_time", ctypes.c_int64),
            ("flags", wintypes.DWORD),
            ("min_ws", ctypes.c_size_t),
            ("max_ws", ctypes.c_size_t),
            ("active", wintypes.DWORD),
            ("affinity", ctypes.c_size_t),
            ("priority", wintypes.DWORD),
            ("scheduling", wintypes.DWORD),
        ]

    class IO(ctypes.Structure):
        _fields_ = [
            (name, ctypes.c_uint64)
            for name in (
                "read_ops",
                "write_ops",
                "other_ops",
                "read_bytes",
                "write_bytes",
                "other_bytes",
            )
        ]

    class Extended(ctypes.Structure):
        _fields_ = [
            ("limits", Limits),
            ("io", IO),
            ("process_mem", ctypes.c_size_t),
            ("job_mem", ctypes.c_size_t),
            ("peak_process", ctypes.c_size_t),
            ("peak_job", ctypes.c_size_t),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    ]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    job = kernel.CreateJobObjectW(None, None)
    limits = Extended()
    limits.limits.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not job or not kernel.SetInformationJobObject(
        job, 9, ctypes.byref(limits), ctypes.sizeof(limits)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    if not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
        raise ctypes.WinError(ctypes.get_last_error())
    return job  # Keep the handle alive for the lifetime of this supervisor.


def wait_ready(process: subprocess.Popen, url: str) -> None:
    # A laptop may have several days of missed test draws to reconcile.
    # Preserve chronological recovery rather than cancelling it after two minutes.
    deadline = time.monotonic() + 600
    progress_at = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Local service stopped. See .tools/local-preview/*.log")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            pass
        if time.monotonic() >= progress_at:
            print(
                "Синхронизируются локальные данные. Оставьте окно открытым…", flush=True
            )
            progress_at = time.monotonic() + 30
        time.sleep(1)
    raise RuntimeError("Local service did not become ready. See preview logs.")


def main() -> None:
    if os.name != "nt":
        raise RuntimeError("This launcher is for Windows.")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    # No project .env is read: child Python processes use this separate cwd.
    if (RUNTIME / ".env").exists():
        raise RuntimeError("Remove the unexpected .tools/local-preview/.env first.")
    instance = claim_instance()
    if instance is None:
        print("Локальная версия уже запущена или запускается.")
        if "--no-browser" not in sys.argv:
            webbrowser.open(URL)
        return
    children = []
    try:
        for port in (8000, 5173):
            with socket.socket() as probe:
                if probe.connect_ex(("127.0.0.1", port)) == 0:
                    raise RuntimeError(
                        f"Port {port} is occupied. Close its local service first."
                    )
        secret_file = RUNTIME / "session-secret.txt"
        if not secret_file.exists():
            secret_file.write_text(secrets.token_urlsafe(48), encoding="utf-8")
        env = isolated_environment(secret_file.read_text(encoding="utf-8"))
        python = ROOT / ".venv/Scripts/python.exe"
        node = next((ROOT / ".tools/node").glob("node-v*-win-x64/node.exe"), None)
        node = str(node) if node else shutil.which("node")
        vite = ROOT / "frontend/miniapp/node_modules/vite/bin/vite.js"
        if not python.is_file() or not node or not vite.is_file():
            raise RuntimeError("Local Python/Node/dependencies are missing.")
        print("Подготавливаю локальную базу и текущую версию Casper Loto…", flush=True)
        ensure_database()
        run([str(python), "-m", "scripts.migrate_database"], env=env)
        run([str(python), "-m", "scripts.local_preview_setup"], env=env)
        # Docker Desktop is shared with other local projects; keep it outside
        # the job that is terminated when this preview window closes.
        _job = windows_process_job()
        with (
            (RUNTIME / "api.log").open("w", encoding="utf-8") as api_log,
            (RUNTIME / "miniapp.log").open("w", encoding="utf-8") as ui_log,
        ):
            api = subprocess.Popen(
                [
                    str(python),
                    "-m",
                    "uvicorn",
                    "k_loto.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
                cwd=RUNTIME,
                env=env,
                stdout=api_log,
                stderr=api_log,
            )
            children.append(api)
            wait_ready(api, API + "/health")
            ui = subprocess.Popen(
                [
                    node,
                    str(vite),
                    "--mode",
                    "browser",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "5173",
                    "--strictPort",
                ],
                cwd=ROOT / "frontend/miniapp",
                env=env,
                stdout=ui_log,
                stderr=ui_log,
            )
            children.append(ui)
            wait_ready(ui, URL)
            print(
                f"\nГОТОВО: {URL}\nТестовая версия. Прогресс сохраняется на ноутбуке.\n"
                "Оставьте это окно открытым. "
                "Закройте его или нажмите Ctrl+C для остановки.\n",
                flush=True,
            )
            if "--no-browser" not in sys.argv:
                webbrowser.open(URL)
            while all(p.poll() is None for p in children):
                time.sleep(1)
            raise RuntimeError("A local service stopped. See preview logs.")
    except KeyboardInterrupt:
        print("Локальная версия остановлена. Прогресс сохранён.")
    finally:
        for process in reversed(children):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
        instance.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        sys.exit(1)
