from __future__ import annotations

from handoff.config import Config
from handoff.mcp_config import FALKORDB_MCP_PACKAGE, falkordb_server_entry, handoff_server_entry


def test_falkordb_server_is_pinned_and_strictly_read_only(config: Config) -> None:
    entry = falkordb_server_entry(config)
    assert entry["command"] == "npx"
    assert entry["args"] == ["-y", FALKORDB_MCP_PACKAGE]
    assert FALKORDB_MCP_PACKAGE == "@falkordb/mcpserver@1.3.0"
    assert entry["env"]["FALKORDB_STRICT_READONLY"] == "true"
    assert entry["env"]["FALKORDB_DEFAULT_READONLY"] == "true"
    assert entry["env"]["FALKORDB_PORT"] == str(config.port)


def test_handoff_server_passes_the_role_through(config: Config) -> None:
    entry = handoff_server_entry("/opt/handoff/bin/handoff-mcp", "shop")
    assert entry["command"] == "/opt/handoff/bin/handoff-mcp"
    assert entry["env"]["HANDOFF_ROLE"] == "${HANDOFF_ROLE:-}"
