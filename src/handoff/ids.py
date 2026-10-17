"""Ids and timestamps used across the graph."""

from __future__ import annotations

import hashlib
import socket
import time
import uuid


def new_id() -> str:
    """Return a new random id for nodes Claude Code does not name."""
    return uuid.uuid4().hex


def now_ms() -> int:
    """Return the current time in milliseconds since the epoch."""
    return time.time_ns() // 1_000_000


def person_session_id(cwd: str) -> str:
    """A stable session id for the person using the CLI in a folder on this machine, so
    messages they send have a sender and the graph shows them as a participant."""
    digest = hashlib.sha256(f"{socket.gethostname()}:{cwd}".encode()).hexdigest()
    return f"person-{digest[:12]}"
