"""Tools a session uses to record its own decisions and needs."""

from __future__ import annotations

from handoff.graph import needs as graph_needs
from handoff.graph.decisions import add_decision
from handoff.ids import new_id
from handoff.mcp.context import NO_REQUEST, ToolContext, blank_field, current_request_id
from handoff.redact import redact


def record_decision(ctx: ToolContext, text: str, reason: str, topic: str) -> str:
    """Record a choice made for the current request, why, and its subject."""
    if problem := blank_field(text=text, reason=reason, topic=topic):
        return problem
    request_id = current_request_id(ctx)
    if request_id is None:
        return NO_REQUEST
    decision_id = new_id()
    add_decision(
        ctx.graph,
        request_id=request_id,
        decision_id=decision_id,
        text=redact(text.strip()),
        reason=redact(reason.strip()),
        topic=topic,
        at=ctx.now(),
    )
    return f"Recorded decision {decision_id} on request {request_id}."


def record_need(ctx: ToolContext, for_role: str, text: str) -> str:
    """Record something the current request needs from another role."""
    if problem := blank_field(for_role=for_role, text=text):
        return problem
    request_id = current_request_id(ctx)
    if request_id is None:
        return NO_REQUEST
    need_id = new_id()
    graph_needs.add_need(
        ctx.graph,
        request_id=request_id,
        need_id=need_id,
        text=redact(text.strip()),
        for_role=for_role.strip(),
        at=ctx.now(),
    )
    return f"Recorded need {need_id} for {for_role.strip()}."


def resolve_need(ctx: ToolContext, need_id: str) -> str:
    """Mark a need as handled by this session's current request."""
    request_id = current_request_id(ctx)
    if request_id is None:
        return NO_REQUEST
    if not graph_needs.resolve_need(ctx.graph, need_id=need_id, request_id=request_id):
        return f"No need with id {need_id}."
    return f"Need {need_id} is resolved by request {request_id}."
