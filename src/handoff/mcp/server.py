"""The `handoff-mcp` server: registers the tools and runs over stdio.

This file only wires tools to their logic in record_tools and read_tools.
"""

from __future__ import annotations

import os
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from handoff.config import Config
from handoff.graph.connection import connect
from handoff.mcp import message_tools, read_tools, record_tools
from handoff.mcp.context import ToolContext, context_from_env

INSTRUCTIONS = (
    "handoff connects this Claude Code session to the other sessions working in the same "
    "project. Each request a person sends to a session is recorded automatically, with the "
    "files it changed. Decisions are recorded only through record_decision: other sessions "
    "see a choice (a field name, an API shape, a library, a trade-off) and its reason only "
    "when it is recorded there. record_need tells another role what this request needs from "
    "it; resolve_need closes such a need, using the id shown in handoff. When a person asks "
    "this session to pick up another session's work, handoff for that role holds what was "
    "asked, decided, changed and still needed. why shows the intent behind a file's edits. "
    "send_message reaches every session with a role: a working session sees it on its next "
    "tool call and an idle one is woken."
)


def build_server(ctx: ToolContext) -> MCPServer:
    """Create the server with every tool bound to `ctx`."""
    server = MCPServer("handoff", instructions=INSTRUCTIONS)

    @server.tool(description="Record a choice made for the current request, why, and its topic.")
    def record_decision(
        text: Annotated[str, Field(description="What was chosen, in one sentence.")],
        reason: Annotated[str, Field(description="Why it was chosen over the alternatives.")],
        topic: Annotated[str, Field(description="Short subject, e.g. 'user profile API'.")],
    ) -> str:
        return record_tools.record_decision(ctx, text, reason, topic)

    @server.tool(description="Record something the current request needs from another role.")
    def record_need(
        for_role: Annotated[str, Field(description="Role that must act, e.g. 'backend'.")],
        text: Annotated[str, Field(description="What that role needs to do.")],
    ) -> str:
        return record_tools.record_need(ctx, for_role, text)

    @server.tool(description="Mark another role's need as handled by the current request.")
    def resolve_need(
        need_id: Annotated[str, Field(description="The id shown after 'id' in handoff.")],
    ) -> str:
        return record_tools.resolve_need(ctx, need_id)

    @server.tool(description="List active sessions and what each is working on.")
    def sessions(within_minutes: int = 120) -> str:
        return read_tools.sessions(ctx, within_minutes)

    @server.tool(
        description="Show what a role (or all roles) was asked, decided, changed and needs."
    )
    def handoff(
        role: Annotated[str | None, Field(description="Role to show; omit for all.")] = None,
        since_minutes: Annotated[int, Field(description="How far back to look.")] = 240,
        limit: Annotated[int, Field(description="Most requests to show, 1 to 50.")] = 10,
    ) -> str:
        return read_tools.handoff(ctx, role, since_minutes, limit)

    @server.tool(description="Show the requests and decisions behind changes to a file.")
    def why(
        path: Annotated[str, Field(description="File path, relative to the project or absolute.")],
    ) -> str:
        return read_tools.why(ctx, path)

    @server.tool(description="Send a message to every session with a role; idle ones wake.")
    def send_message(
        to_role: Annotated[str, Field(description="Role to send to, e.g. 'deploy'.")],
        text: Annotated[str, Field(description="The message.")],
        reply_to: Annotated[
            str | None, Field(description="Id of the message or question this answers.")
        ] = None,
    ) -> str:
        return message_tools.send_message(ctx, to_role, text, reply_to)

    return server


def main() -> None:
    """Console-script entry point: serve this session's tools over stdio.

    The database is connected on the first tool call, so the server starts (and its
    tools answer with a clear sentence) even while FalkorDB is down.
    """
    config = Config.from_env()
    ctx = context_from_env(os.environ, cwd=os.getcwd(), connect=lambda: connect(config))
    build_server(ctx).run("stdio")


if __name__ == "__main__":
    main()
