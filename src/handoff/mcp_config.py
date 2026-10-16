"""The MCP server entries a workspace's .mcp.json needs: ours, and FalkorDB's own."""

from __future__ import annotations

from typing import Any

from handoff.config import Config

FALKORDB_MCP_PACKAGE = "@falkordb/mcpserver@1.3.0"  # pinned: the tool list was checked here


def handoff_server_entry(command: str) -> dict[str, Any]:
    """Our server. Claude Code expands ${VAR} in .mcp.json, so each terminal's
    HANDOFF_ROLE reaches its own copy of the server."""
    return {
        "command": command,
        "env": {
            "HANDOFF_ROLE": "${HANDOFF_ROLE:-}",
            "HANDOFF_GRAPH": "${HANDOFF_GRAPH:-handoff}",
            "HANDOFF_MODEL": "${HANDOFF_MODEL:-claude-code}",
        },
    }


def falkordb_server_entry(config: Config) -> dict[str, Any]:
    """FalkorDB's official MCP server, so agents can write their own Cypher over both
    graphs. Strictly read-only: write queries and delete_graph are refused."""
    return {
        "command": "npx",
        "args": ["-y", FALKORDB_MCP_PACKAGE],
        "env": {
            "FALKORDB_HOST": config.host,
            "FALKORDB_PORT": str(config.port),
            "FALKORDB_DEFAULT_READONLY": "true",
            "FALKORDB_STRICT_READONLY": "true",
        },
    }
