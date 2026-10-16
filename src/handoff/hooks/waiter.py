"""The background waiter, run as `handoff-hook wait` with asyncRewake.

Claude Code starts it when a session stops. It polls for messages to the session's
role; when one arrives it prints it to stderr and exits 2, which wakes the session
even if it is idle. With nothing to deliver it exits 0. One waiter per session.
"""

from __future__ import annotations

import fcntl
import json
import logging
import sys
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

from falkordb import Graph

from handoff.config import Config
from handoff.graph.connection import connect
from handoff.hooks.delivery import pending_messages_text
from handoff.hooks.identity import project_and_role
from handoff.hooks.logs import is_outage, setup_logging
from handoff.ids import now_ms

WAKE = 2
log = logging.getLogger("handoff.waiter")


@contextmanager
def _session_lock(home: Path, session_id: str) -> Iterator[bool]:
    locks = home / "locks"
    locks.mkdir(parents=True, exist_ok=True)
    with (locks / f"{session_id}.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def wait_for_messages(
    config: Config, *, session_id: str, role: str, seconds: float, poll: float
) -> str:
    """Poll until messages arrive (returns their text) or time runs out (returns '')."""
    deadline = time.monotonic() + seconds
    graph: Graph | None = None
    while True:
        try:
            graph = graph or connect(config)
            text = pending_messages_text(graph, session_id=session_id, role=role, at=now_ms())
            if text:
                return text
        except Exception as exc:
            if not is_outage(exc):
                raise
            graph = None  # reconnect on the next poll
        if time.monotonic() >= deadline:
            return ""
        time.sleep(poll)


def main(stdin: str, env: Mapping[str, str]) -> int:
    """Wait for this session's messages. Returns the exit code: 2 to wake, else 0."""
    try:
        config = Config.from_env(env)
        setup_logging(config)
        data = json.loads(stdin)
        _, role = project_and_role(data, env)
        with _session_lock(config.home, str(data["session_id"])) as mine:
            if not mine:
                return 0
            text = wait_for_messages(
                config,
                session_id=str(data["session_id"]),
                role=role,
                seconds=float(env.get("HANDOFF_WAIT_SECONDS", "3500")),
                poll=float(env.get("HANDOFF_WAIT_POLL", "2")),
            )
    except Exception:
        log.exception("waiter failed")
        return 0
    if not text:
        return 0
    sys.stderr.write(text + "\n")
    return WAKE
