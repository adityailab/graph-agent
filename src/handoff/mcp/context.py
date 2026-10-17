"""What every tool needs: the graph, this session's role and project, and the clock."""

from __future__ import annotations

import functools
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from falkordb import Graph
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from handoff.config import resolve_role
from handoff.embed import Embedder
from handoff.graph.schema import ensure_schema
from handoff.ids import now_ms

NO_REQUEST = "Not recorded: no request is recorded for this session yet."
UNREACHABLE = "Not done: the handoff graph is unreachable right now, so nothing was saved or read."
_OUTAGE = (RedisConnectionError, RedisTimeoutError)


class ToolContext:
    """The graph (connected on first use), this session's role and folder, and a clock."""

    def __init__(
        self,
        *,
        role: str,
        cwd: str,
        graph: Graph | None = None,
        connect: Callable[[], Graph] | None = None,
        now: Callable[[], int] = now_ms,
        session_id: str | None = None,
        pid: int | None = None,
        embedder: Embedder | None = None,
        knowledge: Any = None,
    ) -> None:
        self.role, self.cwd, self.now = role, cwd, now
        self.knowledge = knowledge  # handoff.knowledge.startup.Knowledge, when running
        self.embedder = embedder  # None: decisions are stored and searched without vectors
        # From Claude Code, when it provides them. The pid survives /clear; the id does not.
        self.session_id, self.pid = session_id, pid
        self._graph, self._connect = graph, connect
        self.insights_checked_at: int | None = None  # when this server last refreshed them

    @classmethod
    def lazy(
        cls,
        *,
        connect: Callable[[], Graph],
        role: str,
        cwd: str,
        session_id: str | None = None,
        pid: int | None = None,
        embedder: Embedder | None = None,
        knowledge: Any = None,
    ) -> ToolContext:
        """A context that connects, and applies the schema, on the first tool call."""
        return cls(
            role=role,
            cwd=cwd,
            connect=connect,
            session_id=session_id,
            pid=pid,
            embedder=embedder,
            knowledge=knowledge,
        )

    @property
    def graph(self) -> Graph:
        if self._graph is None:
            if self._connect is None:
                raise RuntimeError("ToolContext has neither a graph nor a way to connect")
            graph = self._connect()
            ensure_schema(graph)
            self._graph = graph
        return self._graph


def context_from_env(
    env: Mapping[str, str],
    *,
    cwd: str,
    connect: Callable[[], Graph],
    embedder: Embedder | None = None,
    knowledge: Any = None,
) -> ToolContext:
    """Build the server's context: resolved project folder and normalised role."""
    project = str(Path(env.get("CLAUDE_PROJECT_DIR") or cwd).resolve())
    return ToolContext.lazy(
        connect=connect,
        role=resolve_role(project, env),
        cwd=project,
        session_id=env.get("CLAUDE_CODE_SESSION_ID") or None,
        pid=int(env["CLAUDE_PID"]) if env.get("CLAUDE_PID", "").isdigit() else None,
        embedder=embedder,
        knowledge=knowledge,
    )


def guarded[**P](tool: Callable[P, str]) -> Callable[P, str]:
    """Turn a database outage into a sentence the agent can act on."""

    @functools.wraps(tool)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> str:
        try:
            return tool(*args, **kwargs)
        except _OUTAGE:
            return UNREACHABLE

    return wrapper


def blank_field(**fields: str) -> str | None:
    """Return a refusal naming the first empty field, or None if all are filled."""
    for name, value in fields.items():
        if not value.strip():
            return f"Not recorded: {name} is empty."
    return None
