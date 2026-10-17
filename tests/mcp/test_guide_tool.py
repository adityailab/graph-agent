from __future__ import annotations

import json
from pathlib import Path

from falkordb import Graph

from handoff.config import Config
from handoff.mcp.context import ToolContext
from handoff.mcp.guide_tool import graph_guide


def test_the_tool_uses_this_workspaces_graph_and_servers(
    two_sessions: Graph, config: Config, tmp_path: Path
) -> None:
    (tmp_path / ".mcp.json").write_text(json.dumps({"mcpServers": {"falkordb": {}}}))
    ctx = ToolContext(graph=two_sessions, role="backend", cwd=str(tmp_path))
    text = graph_guide(ctx, config)
    assert f"`{config.graph_name}`" in text
    assert "query_graph_readonly" in text
    assert "not installed" not in text


def test_without_falkordbs_server_in_the_folder_the_tool_says_so(
    two_sessions: Graph, config: Config, tmp_path: Path
) -> None:
    ctx = ToolContext(graph=two_sessions, role="backend", cwd=str(tmp_path))
    assert "not installed" in graph_guide(ctx, config)
