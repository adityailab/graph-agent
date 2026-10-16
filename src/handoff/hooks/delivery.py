"""What a hook tells a live session: messages for it, and needs waiting on its role."""

from __future__ import annotations

from falkordb import Graph

from handoff.format import render_messages
from handoff.graph.messages import claim_pending_messages
from handoff.graph.needs import count_open_needs

MESSAGE_WINDOW_MS = 24 * 60 * 60_000


def pending_messages_text(graph: Graph, *, session_id: str, role: str, at: int) -> str:
    """Claim this session's undelivered messages and render them ('' if none)."""
    messages = claim_pending_messages(
        graph, session_id=session_id, role=role, since=at - MESSAGE_WINDOW_MS, at=at
    )
    return render_messages(messages)


def open_needs_text(graph: Graph, role: str) -> str:
    """A one-line count of open needs addressed to this role ('' if none)."""
    count = count_open_needs(graph, role)
    if count == 0:
        return ""
    noun = "need is" if count == 1 else "needs are"
    return f"{count} open {noun} addressed to {role}; handoff shows them with their ids."
