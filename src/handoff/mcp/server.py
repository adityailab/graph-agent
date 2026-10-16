"""The `handoff-mcp` server: registers the tools and runs over stdio.

This file only wires things together: each tool module registers its own tools.
"""

from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer

from handoff.config import Config
from handoff.embed import FastEmbedder
from handoff.graph.connection import connect
from handoff.mcp import (
    ask_tool,
    connection_tool,
    message_tools,
    read_tools,
    record_tools,
    search_tool,
)
from handoff.mcp.context import ToolContext, context_from_env
from handoff.models.base import ModelClient
from handoff.models.choose import model_from_env

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
    "tool call, and an idle one is woken when its waiter is running. ask puts a question "
    "to another role and returns at once a stand-in answer, written by a model from that "
    "role's recorded history and labelled as such; the real session also gets the question. "
    "search finds recorded decisions by their words and their meaning, from any role. "
    "connection shows the chain of shared files, decisions and needs linking this "
    "session's work to another role's."
)


def build_server(ctx: ToolContext, standin: ModelClient | None = None) -> MCPServer:
    """Create the server with every tool bound to `ctx`."""
    server = MCPServer("handoff", instructions=INSTRUCTIONS)
    record_tools.register(server, ctx)
    read_tools.register(server, ctx)
    message_tools.register(server, ctx)
    ask_tool.register(server, ctx, standin or model_from_env(os.environ))
    search_tool.register(server, ctx)
    connection_tool.register(server, ctx)
    return server


def main() -> None:
    """Console-script entry point: serve this session's tools over stdio.

    The database is connected on the first tool call, so the server starts (and its
    tools answer with a clear sentence) even while FalkorDB is down.
    """
    config = Config.from_env()
    embedder = FastEmbedder(cache_dir=config.home / "models")
    embedder.warm_up()  # load the model now, not inside the first tool call
    ctx = context_from_env(
        os.environ,
        cwd=os.getcwd(),
        connect=lambda: connect(config),
        embedder=embedder,
    )
    build_server(ctx).run("stdio")


if __name__ == "__main__":
    main()
