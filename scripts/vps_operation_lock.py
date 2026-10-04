"""Hold the VPS publication/maintenance flock across all SSH release stages."""

from collections.abc import Iterator
from contextlib import contextmanager

import paramiko


@contextmanager
def remote_operations_lock(client: paramiko.SSHClient) -> Iterator[None]:
    stdin, stdout, _stderr = client.exec_command(
        "flock -w 60 /run/lock/k-loto-operations.lock "
        "sh -c 'printf \"K_LOTO_LOCKED\\n\"; cat >/dev/null'",
        timeout=70,
    )
    try:
        if stdout.readline().strip() != "K_LOTO_LOCKED":
            raise RuntimeError("VPS maintenance/publication lock unavailable")
        yield
    finally:
        stdin.channel.shutdown_write()
        stdout.channel.settimeout(10)
        stdout.read()
