"""The ask tool: a question to another role, answered at once by a stand-in."""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from handoff.config import normalise_role
from handoff.format import shorten
from handoff.graph.history import requests_for_decisions
from handoff.graph.messages import add_citations, add_message
from handoff.ids import new_id
from handoff.mcp.context import ToolContext, guarded
from handoff.mcp.current import current_session
from handoff.mcp.message_tools import NOT_REGISTERED
from handoff.mcp.search_tool import rank_decisions
from handoff.models.base import ModelClient, ModelUnavailable
from handoff.redact import redact
from handoff.standin.answer import answer
from handoff.standin.context import gather_context

_HISTORY_WINDOW_MS = 7 * 24 * 60 * 60_000
_HISTORY_LIMIT = 15


@guarded
def ask(ctx: ToolContext, role: str, question: str, client: ModelClient) -> str:
    """Deliver a question to a role and return a stand-in answer from its history."""
    if not role.strip():
        return "Not asked: role is empty."
    if not question.strip():
        return "Not asked: question is empty."
    session = current_session(ctx)
    if session is None:
        return NOT_REGISTERED
    target, question_id, now = normalise_role(role), new_id(), ctx.now()
    text = redact(question.strip())
    add_message(
        ctx.graph,
        message_id=question_id,
        from_session_id=session.id,
        to_role=target,
        kind="question",
        text=text,
        reply_to=None,
        at=now,
    )
    matching = rank_decisions(ctx, text, k=5)
    history = gather_context(
        ctx.graph,
        role=target,
        since=now - _HISTORY_WINDOW_MS,
        limit=_HISTORY_LIMIT,
        relevant=requests_for_decisions(ctx.graph, decision_ids=matching, role=target),
    )
    if not history.requests and not history.messages:
        return (
            f"No session with the role {target} has recorded history, so no stand-in answer "
            f"is possible. Question {question_id} was delivered to {target} in case one starts."
        )
    try:
        result = answer(client, history, text)
    except ModelUnavailable as exc:
        return (
            f"Question {question_id} was delivered to {target}. "
            f"No stand-in answer is available: {exc}."
        )
    answer_id, answer_text = new_id(), shorten(redact(result.text), 600)
    add_message(
        ctx.graph,
        message_id=answer_id,
        from_session_id=session.id,
        to_role=target,
        kind="standin_answer",
        text=answer_text,
        reply_to=question_id,
        at=now + 1,
    )
    add_citations(ctx.graph, message_id=answer_id, cited_ids=list(result.cited_ids))
    return (
        f"Stand-in answer for {target} (from its recorded history, not the live session): "
        f"{answer_text}\nSources: {', '.join(result.cited_ids) or 'none'}.\n"
        f"Question {question_id} was also delivered to the {target} session, which can "
        "reply with send_message."
    )


def register(server: MCPServer, ctx: ToolContext, client: ModelClient) -> None:
    """Add the ask tool to the server."""

    @server.tool(
        name="ask",
        description="Ask another role a question; get a stand-in answer from its history now.",
    )
    def _ask(
        role: Annotated[str, Field(description="Role to ask, e.g. 'frontend'.")],
        question: Annotated[str, Field(description="The question, in one or two sentences.")],
    ) -> str:
        return ask(ctx, role, question, client)
