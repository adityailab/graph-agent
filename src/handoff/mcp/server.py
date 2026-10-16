"""The `handoff-mcp` server: registers the tools and runs over stdio.

This file only wires tools to their logic in record_tools and read_tools.
"""

from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer

from handoff.config import Config, resolve_role
from handoff.graph.connection import connect
from handoff.graph.schema import ensure_schema
from handoff.mcp import read_tools, record_tools
from handoff.mcp.context import ToolContext

INSTRUCTIONS = (
    "handoff connects this Claude Code session to the other sessions working in the same "
    "project. Each person's request to a session is recorded automatically, with the files "
    "it changed. Decisions are recorded only when you call record_decision: call it whenever "
    "you choose something another session would need to know (a field name, an API shape, a "
    "library, a trade-off), with the reason. Call record_need when your work needs something "
    "from another role, and resolve_need when you finish something another role needed. When "
    "asked to pick up another session's work, call handoff for that role first. Before "
    "changing a file another session edited, call why for it."
)


def build_server(ctx: ToolContext) -> MCPServer:
    """Create the server with every tool bound to `ctx`."""
    server = MCPServer("handoff", instructions=INSTRUCTIONS)

    @server.tool(description="Record a choice made for the current request, why, and its topic.")
    def record_decision(text: str, reason: str, topic: str) -> str:
        return record_tools.record_decision(ctx, text, reason, topic)

    @server.tool(description="Record something the current request needs from another role.")
    def record_need(for_role: str, text: str) -> str:
        return record_tools.record_need(ctx, for_role, text)

    @server.tool(description="Mark another role's need as handled by the current request.")
    def resolve_need(need_id: str) -> str:
        return record_tools.resolve_need(ctx, need_id)

    @server.tool(description="List active sessions and what each is working on.")
    def sessions(within_minutes: int = 120) -> str:
        return read_tools.sessions(ctx, within_minutes)

    @server.tool(
        description="Show what a role (or all roles) was asked, decided, changed and needs."
    )
    def handoff(role: str | None = None, since_minutes: int = 240, limit: int = 10) -> str:
        return read_tools.handoff(ctx, role, since_minutes, limit)

    @server.tool(description="Show the requests and decisions behind changes to a file.")
    def why(path: str) -> str:
        return read_tools.why(ctx, path)

    return server


def main() -> None:
    """Console-script entry point: serve this session's tools over stdio."""
    config = Config.from_env()
    graph = connect(config)
    ensure_schema(graph)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    role = resolve_role(project_dir, os.environ)
    build_server(ToolContext(graph=graph, role=role, cwd=project_dir)).run("stdio")


if __name__ == "__main__":
    main()
