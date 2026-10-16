"""Which waiter is current for a session.

Each new waiter, and each new prompt, writes a fresh token. A waiter that sees a
token other than its own quits at its next poll, so an old waiter never holds the
session's lock for an hour, and no waiter claims messages while a turn is running.
"""

from __future__ import annotations

import os
from pathlib import Path

from handoff.ids import new_id


def _path(home: Path, session_id: str) -> Path:
    return home / "locks" / f"{session_id}.gen"


def bump(home: Path, session_id: str) -> str:
    """Start a new generation for the session and return its token."""
    path = _path(home, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    token = new_id()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(token)
    os.replace(tmp, path)
    return token


def current(home: Path, session_id: str) -> str | None:
    """Return the session's current generation token, if any."""
    try:
        return _path(home, session_id).read_text().strip()
    except FileNotFoundError:
        return None
