"""The connection tool: how this session's work links to another role's, step by step."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from handoff.config import normalise_role
from handoff.format import shorten
from handoff.graph.paths import connection_path
from handoff.graph.records import PathStep
from handoff.mcp.context import NO_REQUEST, ToolContext, guarded
from handoff.mcp.current import current_request

_NOUN = {"File": "file", "Decision": "decision", "Topic": "topic", "Need": "need",
         "Message": "message", "Request": "request"}  # fmt: skip


def _describe(step: PathStep) -> str:
    noun = _NOUN.get(step.label, step.label.lower())
    return f"{noun} {step.text}" if step.label == "File" else f'{noun} "{shorten(step.text, 80)}"'


def render_connection(steps: Sequence[PathStep], role: str) -> str:
    """Render a path as one chain; edits read as 'changed' rather than as nodes."""
    parts: list[str] = []
    for i, step in enumerate(steps):
        if step.label == "Edit":
            continue
        text = _describe(step)
        if i == 0:
            text = f"this {text}"
        elif i == len(steps) - 1:
            text = f"{role} {text}"
        after_edit = i > 0 and steps[i - 1].label == "Edit"
        if after_edit:
            text = f"changed {text}" if step.label == "File" else f"changed by {text}"
        parts.append(text)
    return f"How this session's work connects to the {role} session's:\n" + " → ".join(parts)


@guarded
def connection(ctx: ToolContext, role: str) -> str:
    """The shortest chain of shared files, decisions, needs and messages to `role`'s work."""
    if not role.strip():
        return "Not traced: role is empty."
    request = current_request(ctx)
    if request is None:
        return NO_REQUEST
    target = normalise_role(role)
    steps = connection_path(ctx.graph, from_request=request.id, to_role=target)
    if steps is None:
        return f"No chain of work links this session's current request to the {target} session."
    return render_connection(steps, target)


def register(server: MCPServer, ctx: ToolContext) -> None:
    """Add the connection tool to the server."""

    @server.tool(
        name="connection",
        description="Show how this session's work links to another role's, step by step.",
    )
    def _connection(
        role: Annotated[str, Field(description="Role to trace to, e.g. 'backend'.")],
    ) -> str:
        return connection(ctx, role)
