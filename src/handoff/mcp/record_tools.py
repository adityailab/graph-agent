"""Tools a session uses to record its own decisions and needs."""

from __future__ import annotations

from handoff.config import normalise_role
from handoff.graph import needs as graph_needs
from handoff.graph.decisions import add_decision
from handoff.ids import new_id
from handoff.mcp.context import NO_REQUEST, ToolContext, blank_field, guarded
from handoff.mcp.current import current_request
from handoff.redact import redact


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
