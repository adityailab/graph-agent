"""The local replay file: hook events saved while the database is unreachable.

Rules: events replay in order; replay stops at the first outage so a hook never
waits on a dead database twice; an event that fails for any other reason is moved
to a dead-letter file instead of being retried forever; files are private (0600).
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import re
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

MAX_REPLAY = 100
_SPOOL, _DEAD, _LOCK = "spool.jsonl", "spool.dead.jsonl", "spool.lock"


@dataclass(frozen=True)
class ReplayResult:
    applied: int
    pending: bool  # events are still waiting, so a new event must queue behind them


@contextmanager
def _locked(home: Path, *, wait: bool) -> Iterator[bool]:
    home.mkdir(parents=True, exist_ok=True)
    with (home / _LOCK).open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX if wait else fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _append_bytes(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "ab") as f:
        f.write(data)


def _rewrite(path: Path, lines: list[bytes]) -> None:
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_TRUNC | os.O_CREAT, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(b"".join(line + b"\n" for line in lines))
    os.replace(tmp, path)


def spool_dir(home: Path, graph_name: str) -> Path:
    """The replay folder for one graph. Saved events carry no graph name, so each graph
    keeps its own: a hook in another workspace must never replay them into its graph."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", graph_name) or "_"
    return home / "spool" / safe


def append(home: Path, event: Mapping[str, Any]) -> None:
    """Add one event to the end of the replay file."""
    line = json.dumps(event, ensure_ascii=False).encode() + b"\n"
    with _locked(home, wait=True):
        _append_bytes(home / _SPOOL, line)


def _decode(line: bytes) -> dict[str, Any] | None:
    try:
        event = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return event if isinstance(event, dict) else None


def replay(
    home: Path,
    apply: Callable[[dict[str, Any]], object],
    *,
    is_outage: Callable[[Exception], bool],
) -> ReplayResult:
    """Apply saved events in order, at most MAX_REPLAY per call."""
    path = home / _SPOOL
    if not path.exists() or path.stat().st_size == 0:
        return ReplayResult(0, pending=False)
    with _locked(home, wait=False) as got_lock:
        if not got_lock:  # another hook is replaying right now
            return ReplayResult(0, pending=True)
        kept: list[bytes] = []
        dead: list[bytes] = []
        applied, stopped = 0, False
        for line in path.read_bytes().splitlines():
            if not line.strip():
                continue
            if stopped or applied >= MAX_REPLAY:
                kept.append(line)
                continue
            event = _decode(line)
            if event is None:
                dead.append(line)
                continue
            try:
                apply(event)
                applied += 1
            except Exception as exc:
                # Broad on purpose, like the hook entry point: any failure is either an
                # outage (stop, retry later) or a bad event (set aside, never retried).
                stopped = is_outage(exc)
                (kept if stopped else dead).append(line)
                if not stopped:
                    log.warning("replay event set aside: %s", type(exc).__name__)
        _rewrite(path, kept)
        if dead:
            _append_bytes(home / _DEAD, b"".join(line + b"\n" for line in dead))
    return ReplayResult(applied, pending=bool(kept))
