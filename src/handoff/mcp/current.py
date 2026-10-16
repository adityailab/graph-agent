"""Which session a tool call comes from, and the request it is working on."""

from __future__ import annotations

from dataclasses import dataclass

from handoff.format import shorten
from handoff.graph.records import SessionInfo
from handoff.graph.requests import latest_request_id, request_text
from handoff.graph.sessions import active_session, count_sessions, get_session, session_for_pid
from handoff.mcp.context import ToolContext

_SHARING_WINDOW_MS = 120 * 60_000


@dataclass(frozen=True)
class CurrentRequest:
    id: str
    text: str
    note: str  # set when other sessions share this role and folder


def _exact_session(ctx: ToolContext) -> SessionInfo | None:
    # The process id first: after /clear the server still holds the old session id,
    # but the same process's newest session is the live one.
    if ctx.pid is not None:
        by_pid = session_for_pid(ctx.graph, pid=ctx.pid, cwd=ctx.cwd)
        if by_pid is not None:
            return by_pid
    return get_session(ctx.graph, ctx.session_id) if ctx.session_id else None


def current_session(ctx: ToolContext) -> SessionInfo | None:
    """Return this session: by Claude Code's process or session id when known, else by
    role and project folder (the most recently seen match)."""
    return _exact_session(ctx) or active_session(ctx.graph, role=ctx.role, cwd=ctx.cwd)


def _sharing_note(ctx: ToolContext) -> str:
    sharing = count_sessions(
        ctx.graph, role=ctx.role, cwd=ctx.cwd, since=ctx.now() - _SHARING_WINDOW_MS
    )
    if sharing <= 1:
        return ""
    return (
        f" Note: {sharing} sessions share the role {ctx.role} in this folder, so this may be "
        "another terminal's request. A distinct HANDOFF_ROLE per terminal keeps them apart."
    )


def current_request(ctx: ToolContext) -> CurrentRequest | None:
    """Return the request this session is working on now, if any."""
    exact = _exact_session(ctx)
    session = exact or active_session(ctx.graph, role=ctx.role, cwd=ctx.cwd)
    request_id = latest_request_id(ctx.graph, session.id) if session else None
    if request_id is None:
        return None
    note = "" if exact else _sharing_note(ctx)
    text = shorten(request_text(ctx.graph, request_id) or "", 80)
    return CurrentRequest(id=request_id, text=text, note=note)
