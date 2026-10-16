"""Which session a tool call comes from, and the request it is working on."""

from __future__ import annotations

from dataclasses import dataclass

from handoff.format import shorten
from handoff.graph.records import SessionInfo
from handoff.graph.requests import latest_request_id, request_text
from handoff.graph.sessions import active_session, count_sessions, get_session
from handoff.mcp.context import ToolContext

_SHARING_WINDOW_MS = 120 * 60_000


@dataclass(frozen=True)
class CurrentRequest:
    id: str
    text: str
    note: str  # set when other sessions share this role and folder


def current_session(ctx: ToolContext) -> SessionInfo | None:
    """Return this session: by Claude Code's session id when known, else by role and
    project folder (the most recently seen match)."""
    if ctx.session_id:
        exact = get_session(ctx.graph, ctx.session_id)
        if exact is not None:
            return exact
    return active_session(ctx.graph, role=ctx.role, cwd=ctx.cwd)


def current_request(ctx: ToolContext) -> CurrentRequest | None:
    """Return the request this session is working on now, if any."""
    session = current_session(ctx)
    request_id = latest_request_id(ctx.graph, session.id) if session else None
    if request_id is None:
        return None
    exact = bool(ctx.session_id) and session is not None and session.id == ctx.session_id
    sharing = (
        0
        if exact
        else count_sessions(
            ctx.graph, role=ctx.role, cwd=ctx.cwd, since=ctx.now() - _SHARING_WINDOW_MS
        )
    )
    note = (
        f" Note: {sharing} sessions share the role {ctx.role} in this folder, so this may be "
        "another terminal's request. A distinct HANDOFF_ROLE per terminal keeps them apart."
        if sharing > 1
        else ""
    )
    text = shorten(request_text(ctx.graph, request_id) or "", 80)
    return CurrentRequest(id=request_id, text=text, note=note)
