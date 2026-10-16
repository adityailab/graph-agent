"""Tools a session uses to record its own decisions and needs."""

from __future__ import annotations

import logging
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from handoff.config import normalise_role
from handoff.graph import needs as graph_needs
from handoff.graph.decisions import add_decision, set_decision_embedding
from handoff.ids import new_id
from handoff.mcp.context import NO_REQUEST, ToolContext, blank_field, guarded
from handoff.mcp.current import current_request
from handoff.redact import redact

log = logging.getLogger(__name__)


def _embed_decision(ctx: ToolContext, decision_id: str, text: str) -> None:
    if ctx.embedder is None:
        return
    try:
        vector = ctx.embedder.embed([redact(text)])[0]
    except Exception:
        # The decision is already saved; search still finds it by its words.
        log.exception("embedding failed for decision %s", decision_id)
        return
    set_decision_embedding(ctx.graph, decision_id, vector)


@guarded
def record_decision(ctx: ToolContext, text: str, reason: str, topic: str) -> str:
    """Record a choice made for the current request, why, and its subject."""
    if problem := blank_field(text=text, reason=reason, topic=topic):
        return problem
    request = current_request(ctx)
    if request is None:
        return NO_REQUEST
    decision_id = new_id()
    add_decision(
        ctx.graph,
        request_id=request.id,
        decision_id=decision_id,
        text=redact(text.strip()),
        reason=redact(reason.strip()),
        topic=topic,
        at=ctx.now(),
    )
    _embed_decision(ctx, decision_id, f"{text.strip()} {reason.strip()}")
    return f'Recorded decision {decision_id} on request "{request.text}".{request.note}'


@guarded
def record_need(ctx: ToolContext, for_role: str, text: str) -> str:
    """Record something the current request needs from another role."""
    if problem := blank_field(for_role=for_role, text=text):
        return problem
    request = current_request(ctx)
    if request is None:
        return NO_REQUEST
    need_id, role = new_id(), normalise_role(for_role)
    graph_needs.add_need(
        ctx.graph,
        request_id=request.id,
        need_id=need_id,
        text=redact(text.strip()),
        for_role=role,
        at=ctx.now(),
    )
    return f'Recorded need {need_id} for {role} on request "{request.text}".{request.note}'


@guarded
def resolve_need(ctx: ToolContext, need_id: str) -> str:
    """Mark a need as handled by this session's current request."""
    request = current_request(ctx)
    if request is None:
        return NO_REQUEST
    if not graph_needs.resolve_need(ctx.graph, need_id=need_id.strip(), request_id=request.id):
        return f"No need with id {need_id}."
    return f'Need {need_id} is resolved by request "{request.text}".{request.note}'


def register(server: MCPServer, ctx: ToolContext) -> None:
    """Add the recording tools to the server."""

    @server.tool(
        name="record_decision",
        description="Record a choice made for the current request, why, and its topic.",
    )
    def _record_decision(
        text: Annotated[str, Field(description="What was chosen, in one sentence.")],
        reason: Annotated[str, Field(description="Why it was chosen over the alternatives.")],
        topic: Annotated[str, Field(description="Short subject, e.g. 'user profile API'.")],
    ) -> str:
        return record_decision(ctx, text, reason, topic)

    @server.tool(
        name="record_need",
        description="Record something the current request needs from another role.",
    )
    def _record_need(
        for_role: Annotated[str, Field(description="Role that must act, e.g. 'backend'.")],
        text: Annotated[str, Field(description="What that role needs to do.")],
    ) -> str:
        return record_need(ctx, for_role, text)

    @server.tool(
        name="resolve_need",
        description="Mark another role's need as handled by the current request.",
    )
    def _resolve_need(
        need_id: Annotated[str, Field(description="The id shown after 'id' in handoff.")],
    ) -> str:
        return resolve_need(ctx, need_id)
