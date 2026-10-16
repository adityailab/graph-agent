from __future__ import annotations

from handoff.graph.messages import claim_pending_messages
from handoff.graph.schema import ensure_schema
from handoff.mcp.context import ToolContext
from handoff.mcp.message_tools import send_message


def test_sent_message_reaches_the_other_role(backend: ToolContext) -> None:
    reply = send_message(backend, " Frontend ", "avatarUrl is live")
    assert reply.startswith("Sent message")
    got = claim_pending_messages(backend.graph, session_id="fe", role="frontend", since=0, at=3_000)
    assert [(m.from_role, m.text) for m in got] == [("backend", "avatarUrl is live")]


def test_blank_message_is_refused(backend: ToolContext) -> None:
    assert send_message(backend, "frontend", "  ") == "Not sent: text is empty."


def test_unregistered_session_cannot_send(backend: ToolContext) -> None:
    ensure_schema(backend.graph)
    ctx = ToolContext(graph=backend.graph, role="deploy", cwd="/w", now=lambda: 2_000)
    assert send_message(ctx, "frontend", "hi").startswith("Not sent: this session")
