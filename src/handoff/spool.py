"""The local replay file: hook events saved while the database is unreachable."""

from __future__ import annotations

import fcntl
import json
import logging
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_SPOOL = "spool.jsonl"
_LOCK = "spool.lock"


@contextmanager
def _locked(home: Path) -> Iterator[None]:
    home.mkdir(parents=True, exist_ok=True)
    with (home / _LOCK).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def append(home: Path, event: Mapping[str, Any]) -> None:
    """Add one event to the end of the replay file."""
    with _locked(home), (home / _SPOOL).open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def replay(home: Path, apply: Callable[[dict[str, Any]], object]) -> int:
    """Apply saved events in order and return how many succeeded.

    Events whose `apply` raises stay in the file, in order, for the next replay.
    Lines that are not valid JSON can never succeed, so they are dropped.
    """
    path = home / _SPOOL
    if not path.exists():
        return 0
    with _locked(home):
        lines = path.read_text(encoding="utf-8").splitlines()
        kept: list[str] = []
        applied = 0
        for line in lines:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                log.warning("dropping unreadable replay line: %.80s", line)
                continue
            try:
                apply(event)
                applied += 1
            except Exception:
                # Broad on purpose, like the hook entry point: whatever stopped this
                # event (database still down, a bug), it is kept and retried later.
                kept.append(line)
        path.write_text("".join(f"{k}\n" for k in kept), encoding="utf-8")
    return applied
