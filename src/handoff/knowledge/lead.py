"""Which knowledge worker leads for a graph: one file lock per graph and server."""

from __future__ import annotations

import fcntl
from pathlib import Path

from handoff.config import Config


def lock_name(config: Config) -> str:
    """The lock's name: one worker per graph per server, on this machine."""
    return f"{config.host}-{config.port}-{config.graph_name}"


def lock_path(config: Config) -> Path:
    """Where the lead lock lives (the worker builds the same path from lock_name)."""
    return config.home / "locks" / f"knowledge-{lock_name(config)}.lock"


def is_leading(config: Config) -> bool:
    """True if some process holds the lead lock, i.e. a knowledge worker is running."""
    path = lock_path(config)
    if not path.exists():
        return False
    with path.open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle, fcntl.LOCK_UN)
        return False
