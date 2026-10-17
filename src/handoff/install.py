"""Setting up a workspace: hooks in .claude/settings.local.json, servers in .mcp.json.

Existing settings, hooks and servers are kept; running it again changes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from handoff.config import Config, graph_for_workspace
from handoff.mcp_config import falkordb_server_entry, handoff_server_entry

_OURS = "handoff-hook"


def _hook_groups(bin_dir: Path) -> dict[str, list[dict[str, Any]]]:
    hook = {"type": "command", "command": str(bin_dir / _OURS)}
    waiter = {
        "type": "command",
        "command": f"{bin_dir / _OURS} wait",
        "asyncRewake": True,  # wakes an idle session when a message arrives
        "timeout": 3600,
    }
    return {
        "SessionStart": [{"hooks": [hook]}],
        "UserPromptSubmit": [{"hooks": [hook]}],
        "PostToolUse": [{"matcher": "*", "hooks": [hook]}],
        "Stop": [{"hooks": [hook, waiter]}],
    }


def _is_ours(group: dict[str, Any]) -> bool:
    return any(_OURS in str(h.get("command", "")) for h in group.get("hooks", []))


def _merge_hooks(settings: dict[str, Any], bin_dir: Path) -> None:
    hooks = settings.setdefault("hooks", {})
    for event, groups in _hook_groups(bin_dir).items():
        kept = [g for g in hooks.get(event, []) if not _is_ours(g)]  # replaces an old install
        hooks[event] = kept + groups


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data: dict[str, Any] = json.loads(path.read_text() or "{}")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def _instructions(workspace: Path, graph: str, falkordb_mcp: bool) -> str:
    roles = "\n".join(f"     HANDOFF_ROLE={r} claude" for r in ("frontend", "backend", "deploy"))
    extra = (
        "\nThe FalkorDB MCP server (read-only) runs through npx, which needs Node 18 or later."
        if falkordb_mcp
        else ""
    )
    return (
        f"handoff is set up in {workspace}, on its own graph {graph}.\n\n"
        "1. Start FalkorDB from the handoff folder:  docker compose up -d\n"
        f"   (graph browser: http://localhost:3000, graph {graph})\n"
        f"2. In {workspace}, open one terminal per role and start Claude Code with it:\n"
        f"{roles}\n"
        "   Claude Code asks once to approve the project's MCP servers.\n"
        "3. Optional, for the knowledge graph (needs the 'knowledge' extra):\n"
        f"     HANDOFF_GRAPH={graph} handoff-knowledge"
        f"{extra}"
    )


def install(
    workspace: Path,
    *,
    bin_dir: Path,
    config: Config,
    falkordb_mcp: bool = True,
    graph: str | None = None,
) -> str:
    """Install hooks and MCP servers into `workspace`; return what to do next.

    The workspace gets a graph of its own (HANDOFF_GRAPH in its settings), unless `graph`
    names one or its settings already choose one."""
    settings_path = workspace / ".claude" / "settings.local.json"
    settings = _read_json(settings_path)
    _merge_hooks(settings, bin_dir)
    env = settings.setdefault("env", {})
    if graph:
        env["HANDOFF_GRAPH"] = graph
    env.setdefault("HANDOFF_GRAPH", graph_for_workspace(workspace))
    _write_json(settings_path, settings)

    mcp_path = workspace / ".mcp.json"
    mcp = _read_json(mcp_path)
    servers = mcp.setdefault("mcpServers", {})
    servers["handoff"] = handoff_server_entry(str(bin_dir / "handoff-mcp"), env["HANDOFF_GRAPH"])
    if falkordb_mcp:
        servers["falkordb"] = falkordb_server_entry(config)
    else:
        servers.pop("falkordb", None)
    _write_json(mcp_path, mcp)
    return _instructions(workspace, env["HANDOFF_GRAPH"], falkordb_mcp)
