"""What every tool needs: the graph, this session's role and project, and the clock."""

from __future__ import annotations

import functools
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from falkordb import Graph
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from handoff.config import resolve_role
from handoff.format import shorten
from handoff.graph.records import SessionInfo
from handoff.graph.requests import latest_request_id, request_text
from handoff.graph.schema import ensure_schema
from handoff.graph.sessions import active_session, count_sessions
from handoff.ids import now_ms

NO_REQUEST = "Not recorded: no request is recorded for this session yet."
UNREACHABLE = "Not done: the handoff graph is unreachable right now, so nothing was saved or read."
_OUTAGE = (RedisConnectionError, RedisTimeoutError)
_SHARING_WINDOW_MS = 120 * 60_000


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
    ) -> None:
        self.role, self.cwd, self.now = role, cwd, now
        self._graph, self._connect = graph, connect

    @classmethod
    def lazy(cls, *, connect: Callable[[], Graph], role: str, cwd: str) -> ToolContext:
        """A context that connects, and applies the schema, on the first tool call."""
        return cls(role=role, cwd=cwd, connect=connect)

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
    env: Mapping[str, str], *, cwd: str, connect: Callable[[], Graph]
) -> ToolContext:
    """Build the server's context: resolved project folder and normalised role."""
    project = str(Path(env.get("CLAUDE_PROJECT_DIR") or cwd).resolve())
    return ToolContext.lazy(connect=connect, role=resolve_role(project, env), cwd=project)


def guarded[**P](tool: Callable[P, str]) -> Callable[P, str]:
    """Turn a database outage into a sentence the agent can act on."""

    @functools.wraps(tool)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> str:
        try:
            return tool(*args, **kwargs)
        except _OUTAGE:
            return UNREACHABLE

    return wrapper


@dataclass(frozen=True)
class CurrentRequest:
    id: str
    text: str
    note: str  # set when other sessions share this role and folder


def current_session(ctx: ToolContext) -> SessionInfo | None:
    """Return this session, found by role and project folder."""
    return active_session(ctx.graph, role=ctx.role, cwd=ctx.cwd)


def current_request(ctx: ToolContext) -> CurrentRequest | None:
    """Return the request this session is working on now, if any."""
    session = current_session(ctx)
    request_id = latest_request_id(ctx.graph, session.id) if session else None
    if request_id is None:
        return None
    sharing = count_sessions(
        ctx.graph, role=ctx.role, cwd=ctx.cwd, since=ctx.now() - _SHARING_WINDOW_MS
    )
    note = (
        f" Note: {sharing} sessions share the role {ctx.role} in this folder, so this may be "
        "another terminal's request. A distinct HANDOFF_ROLE per terminal keeps them apart."
        if sharing > 1
        else ""
    )
    text = shorten(request_text(ctx.graph, request_id) or "", 80)
    return CurrentRequest(id=request_id, text=text, note=note)


def blank_field(**fields: str) -> str | None:
    """Return a refusal naming the first empty field, or None if all are filled."""
    for name, value in fields.items():
        if not value.strip():
            return f"Not recorded: {name} is empty."
    return None
