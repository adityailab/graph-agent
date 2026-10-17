"""Tools a session uses to read what the other sessions asked, decided and changed."""

from __future__ import annotations

import os
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from handoff.config import normalise_role
from handoff.format import render_handoff, render_why, select_requests, shorten
from handoff.graph.consultations import add_consultations
from handoff.graph.edits import why_file
from handoff.graph.history import handoff_requests
from handoff.graph.overlaps import shared_files
from handoff.graph.requests import latest_request_id, request_text
from handoff.graph.sessions import active_sessions
from handoff.mcp.context import ToolContext, guarded
from handoff.mcp.current import current_request, current_session
from handoff.mcp.insights_view import insights_section
from handoff.paths import relative_path

_MINUTE_MS = 60_000
_WEEK_MINUTES = 7 * 24 * 60


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


@guarded
def sessions(ctx: ToolContext, within_minutes: int = 120) -> str:
    """List sessions seen recently, with the request each is working on."""
    minutes = _clamp(within_minutes, 1, _WEEK_MINUTES)
    found = active_sessions(ctx.graph, since=ctx.now() - minutes * _MINUTE_MS)
    me = current_session(ctx)
    lines = []
    for s in found:
        label = f"{s.role} (this session)" if me and s.id == me.id else s.role
        request_id = latest_request_id(ctx.graph, s.id)
        text = request_text(ctx.graph, request_id) if request_id else None
        lines.append(
            f'{label}: working on "{shorten(text)}"' if text else f"{label}: no request yet"
        )
    return "\n".join(lines) or f"No sessions active in the last {minutes} minutes."


@guarded
def handoff(
    ctx: ToolContext, role: str | None = None, since_minutes: int = 240, limit: int = 10
) -> str:
    """Show what a role (or every role) was asked, decided, changed and needs."""
    minutes = _clamp(since_minutes, 0, _WEEK_MINUTES)
    since = ctx.now() - minutes * _MINUTE_MS
    requests = handoff_requests(
        ctx.graph, role=normalise_role(role) if role and role.strip() else None, since=since
    )
    selected = select_requests(requests, _clamp(limit, 1, 50))
    text = render_handoff(selected)
    reader = current_request(ctx)
    if reader is not None and selected:
        add_consultations(
            ctx.graph, request_id=reader.id, consulted_ids=[r.id for r in selected], at=ctx.now()
        )
    shared = shared_files(ctx.graph, since=since)
    if shared:
        listed = "; ".join(f"{f.path} ({', '.join(f.roles)})" for f in shared)
        text += f"\n\nChanged by more than one role: {listed}"
    matters = insights_section(ctx)
    return f"{text}\n\n{matters}" if matters else text


@guarded
def why(ctx: ToolContext, path: str) -> str:
    """Show the requests and decisions behind changes to a file."""
    rel = relative_path(path, ctx.cwd) if os.path.isabs(path) else os.path.normpath(path)
    rows = why_file(ctx.graph, rel)
    return render_why(rel, rows) if rows else f"No recorded edits to {rel}."


def register(server: MCPServer, ctx: ToolContext) -> None:
    """Add the reading tools to the server."""

    @server.tool(name="sessions", description="List active sessions and what each is working on.")
    def _sessions(within_minutes: int = 120) -> str:
        return sessions(ctx, within_minutes)

    @server.tool(
        name="handoff",
        description="Show what a role (or all roles) was asked, decided, changed and needs.",
    )
    def _handoff(
        role: Annotated[str | None, Field(description="Role to show; omit for all.")] = None,
        since_minutes: Annotated[int, Field(description="How far back to look.")] = 240,
        limit: Annotated[int, Field(description="Most requests to show, 1 to 50.")] = 10,
    ) -> str:
        return handoff(ctx, role, since_minutes, limit)

    @server.tool(
        name="why", description="Show the requests and decisions behind changes to a file."
    )
    def _why(
        path: Annotated[str, Field(description="File path, relative to the project or absolute.")],
    ) -> str:
        return why(ctx, path)
