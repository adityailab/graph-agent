"""What a hook tells a live session: messages for it, and needs waiting on its role."""

from __future__ import annotations

from falkordb import Graph

from handoff.format import render_messages, shorten
from handoff.graph.messages import claim_pending_messages, has_pending_messages
from handoff.graph.needs import count_open_needs
from handoff.graph.overlaps import recent_edits_by_others

MESSAGE_WINDOW_MS = 24 * 60 * 60_000


def pending_messages_text(graph: Graph, *, session_id: str, role: str, at: int) -> str:
    """Claim this session's undelivered messages and render them ('' if none)."""
    since = at - MESSAGE_WINDOW_MS
    if not has_pending_messages(graph, session_id=session_id, role=role, since=since):
        return ""
    messages = claim_pending_messages(graph, session_id=session_id, role=role, since=since, at=at)
    return render_messages(messages)


def open_needs_text(graph: Graph, role: str) -> str:
    """A one-line count of open needs addressed to this role ('' if none)."""
    count = count_open_needs(graph, role)
    if count == 0:
        return ""
    noun = "need is" if count == 1 else "needs are"
    return f"{count} open {noun} addressed to {role}; handoff shows them with their ids."


COLLISION_WINDOW_MS = 2 * 60 * 60_000


def collision_text(graph: Graph, *, path: str, session_id: str, at: int) -> str:
    """Facts about other sessions that changed this file recently ('' if none)."""
    others = recent_edits_by_others(
        graph, path=path, session_id=session_id, since=at - COLLISION_WINDOW_MS
    )
    return "\n".join(
        f"{path} was also changed by the {o.role} session {max(0, (at - o.at) // 60_000)} "
        f'min ago, for the request "{shorten(o.request_text, 120)}". why shows the intent '
        "behind its edits."
        for o in others
    )
