"""What every tool needs: the graph, this session's role and project, and the clock."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from falkordb import Graph

from handoff.graph.requests import latest_request_id
from handoff.graph.sessions import active_session
from handoff.ids import now_ms

NO_REQUEST = "Not recorded: no request is recorded for this session yet."


@dataclass(frozen=True)
class ToolContext:
    graph: Graph
    role: str
    cwd: str
    now: Callable[[], int] = now_ms


def current_request_id(ctx: ToolContext) -> str | None:
    """Return the request this session is working on now, if any."""
    session = active_session(ctx.graph, role=ctx.role, cwd=ctx.cwd)
    return latest_request_id(ctx.graph, session.id) if session else None


def blank_field(**fields: str) -> str | None:
    """Return a refusal naming the first empty field, or None if all are filled."""
    for name, value in fields.items():
        if not value.strip():
            return f"Not recorded: {name} is empty."
    return None
