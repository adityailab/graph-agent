"""Detached helper processes of the demo (the driver, mission control) and their pid files."""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
from pathlib import Path


def stop_from_pid_file(pid_file: Path) -> None:
    """Stop the process an earlier run left behind (it would keep running into the new run)."""
    try:
        pid = int(pid_file.read_text())
    except (OSError, ValueError):
        return
    pid_file.unlink(missing_ok=True)
    with contextlib.suppress(ProcessLookupError):  # already finished
        os.kill(pid, signal.SIGTERM)


def start_detached(
    command: list[str], *, log: Path, pid_file: Path, cwd: Path | None = None
) -> None:
    """Run `command` detached from this terminal, replacing any earlier one. Its pid and log
    live in handoff's own state folder, outside the scratch project that is reset."""
    log.parent.mkdir(parents=True, exist_ok=True)
    stop_from_pid_file(pid_file)
    with log.open("w") as out:
        proc = subprocess.Popen(  # noqa: S603 - our own command, no shell
            command,
            stdout=out,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            cwd=cwd,
        )
    pid_file.write_text(str(proc.pid))
