"""Tools for temporal memory (how decisions changed) and procedural memory (standing rules)."""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from handoff.config import normalise_role
from handoff.format import render_conventions, render_timeline
from handoff.graph import conventions as graph_conventions
from handoff.graph.decisions import normalise_topic
from handoff.graph.timeline import supersede_decision as graph_supersede
from handoff.graph.timeline import topic_timeline
from handoff.ids import new_id
from handoff.mcp.context import ToolContext, blank_field, guarded
from handoff.redact import redact


@guarded
def supersede_decision(ctx: ToolContext, decision_id: str, replaces: str) -> str:
    """Say that a decision replaces an earlier one; the old one stays in the timeline."""
    if problem := blank_field(decision_id=decision_id, replaces=replaces):
        return problem
    if not graph_supersede(
        ctx.graph, new_id=decision_id.strip(), old_id=replaces.strip(), at=ctx.now()
    ):
        return "Not recorded: one of those decision ids does not exist."
    return f"Decision {decision_id.strip()} now replaces {replaces.strip()}."


@guarded
def timeline(ctx: ToolContext, topic: str) -> str:
    """How decisions about a topic changed over time, oldest first."""
    if problem := blank_field(topic=topic):
        return problem
    entries = topic_timeline(ctx.graph, topic)
    if not entries:
        return f"No decisions recorded about {topic.strip()}."
    return render_timeline(normalise_topic(topic), entries)


@guarded
def record_convention(ctx: ToolContext, rule: str, reason: str, scope: str = "all") -> str:
    """Record a standing rule for every role, or for one role."""
    if problem := blank_field(rule=rule, reason=reason):
        return problem
    scope_name = normalise_role(scope) if scope.strip() else graph_conventions.ALL
    convention_id = new_id()
    graph_conventions.add_convention(
        ctx.graph,
        convention_id=convention_id,
        text=redact(rule.strip()),
        reason=redact(reason.strip()),
        scope=scope_name,
        author=ctx.role,
        at=ctx.now(),
    )
    return f"Recorded convention {convention_id} for {scope_name}."


@guarded
def conventions(ctx: ToolContext) -> str:
    """The standing rules in force for this session's role."""
    found = graph_conventions.conventions_for(ctx.graph, ctx.role)
    if not found:
        return f"No conventions are in force for {ctx.role}."
    return render_conventions(found)


@guarded
def retire_convention(ctx: ToolContext, convention_id: str) -> str:
    """Stop a standing rule applying."""
    if problem := blank_field(convention_id=convention_id):
        return problem
    if not graph_conventions.retire_convention(ctx.graph, convention_id.strip(), at=ctx.now()):
        return f"No convention with id {convention_id.strip()}."
    return f"Convention {convention_id.strip()} is retired."


def register(server: MCPServer, ctx: ToolContext) -> None:
    """Add the memory tools to the server."""

    @server.tool(
        name="supersede_decision",
        description="Say that a decision replaces an earlier one (both stay in the timeline).",
    )
    def _supersede(
        decision_id: Annotated[str, Field(description="The new decision's id.")],
        replaces: Annotated[str, Field(description="The id of the decision it replaces.")],
    ) -> str:
        return supersede_decision(ctx, decision_id, replaces)

    @server.tool(
        name="timeline",
        description="How decisions about a topic changed over time, and what replaced what.",
    )
    def _timeline(topic: Annotated[str, Field(description="The topic, e.g. 'profile'.")]) -> str:
        return timeline(ctx, topic)

    @server.tool(
        name="record_convention",
        description="Record a standing rule (a convention) for every role or one role.",
    )
    def _record_convention(
        rule: Annotated[str, Field(description="The rule, in one sentence.")],
        reason: Annotated[str, Field(description="Why the team follows it.")],
        scope: Annotated[str, Field(description="'all' (default) or one role.")] = "all",
    ) -> str:
        return record_convention(ctx, rule, reason, scope)

    @server.tool(
        name="conventions", description="The standing rules in force for this session's role."
    )
    def _conventions() -> str:
        return conventions(ctx)

    @server.tool(name="retire_convention", description="Stop a standing rule applying.")
    def _retire(
        convention_id: Annotated[str, Field(description="The id shown by conventions.")],
    ) -> str:
        return retire_convention(ctx, convention_id)
