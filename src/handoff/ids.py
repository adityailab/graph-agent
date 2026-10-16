"""Ids and timestamps used across the graph."""

from __future__ import annotations

import time
import uuid


def new_id() -> str:
    """Return a new random id for nodes Claude Code does not name."""
    return uuid.uuid4().hex


def now_ms() -> int:
    """Return the current time in milliseconds since the epoch."""
    return time.time_ns() // 1_000_000
