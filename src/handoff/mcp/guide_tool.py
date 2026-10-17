"""The graph_guide tool: everything a session needs to write its own Cypher."""

from __future__ import annotations

import json
import os
from pathlib import Path

from falkordb import Graph
from mcp.server.mcpserver import MCPServer

from handoff.config import Config, knowledge_graph_name
from handoff.graph.connection import connect, graph_exists
from handoff.guide.build import build_guide
from handoff.mcp.context import ToolContext, guarded


def _falkordb_server_installed(cwd: str) -> bool:
    # handoff ask brings its own FalkorDB server and says so; otherwise read the folder's.
    if os.environ.get("HANDOFF_FALKORDB_MCP") in ("on", "off"):
        return os.environ["HANDOFF_FALKORDB_MCP"] == "on"
    try:
        data = json.loads((Path(cwd) / ".mcp.json").read_text())
    except (OSError, ValueError):
        return False
    servers = data.get("mcpServers") if isinstance(data, dict) else None
    return isinstance(servers, dict) and "falkordb" in servers


def _knowledge_graph(config: Config) -> Graph | None:
    kg_config = Config(config.host, config.port, knowledge_graph_name(config), config.home)
    return connect(kg_config) if graph_exists(kg_config) else None


@guarded
def graph_guide(ctx: ToolContext, config: Config) -> str:
    """How to query this project's graphs directly with read-only Cypher."""
    return build_guide(
        ctx.graph,
        _knowledge_graph(config),
        graph_name=config.graph_name,
        kg_name=knowledge_graph_name(config),
        falkordb_mcp=_falkordb_server_installed(ctx.cwd),
    )


def register(server: MCPServer, ctx: ToolContext, config: Config) -> None:
    """Add graph_guide to the server."""

    @server.tool(
        name="graph_guide",
        description=(
            "How to query this project's graphs yourself with read-only Cypher: graph names, "
            "what each node and relationship means, live counts, indexes, FalkorDB rules and "
            "ready recipes (search, PageRank, betweenness, components)."
        ),
    )
    def graph_guide_tool() -> str:
        return graph_guide(ctx, config)
