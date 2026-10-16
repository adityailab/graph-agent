"""Tools a session uses to talk to other sessions."""

from __future__ import annotations

from handoff.config import normalise_role
from handoff.graph.messages import add_message
from handoff.ids import new_id
from handoff.mcp.context import ToolContext, current_session, guarded
from handoff.redact import redact

NOT_REGISTERED = "Not sent: this session is not registered yet; it is after its first prompt."


@guarded
def send_message(ctx: ToolContext, to_role: str, text: str, reply_to: str | None = None) -> str:
    """Send text to every session with `to_role`; idle ones are woken."""
    if not to_role.strip():
        return "Not sent: to_role is empty."
    if not text.strip():
        return "Not sent: text is empty."
    session = current_session(ctx)
    if session is None:
        return NOT_REGISTERED
    message_id, role = new_id(), normalise_role(to_role)
    add_message(
        ctx.graph,
        message_id=message_id,
        from_session_id=session.id,
        to_role=role,
        kind="message",
        text=redact(text.strip()),
        reply_to=reply_to.strip() if reply_to and reply_to.strip() else None,
        at=ctx.now(),
    )
    return f"Sent message {message_id} to {role}."
