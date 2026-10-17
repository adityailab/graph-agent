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


class InstallError(ValueError):
    """A settings file handoff would change is not in a shape it can safely merge into."""


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


def _section(data: dict[str, Any], key: str, path: Path) -> dict[str, Any]:
    section = data.setdefault(key, {})
    if not isinstance(section, dict):
        raise InstallError(f'"{key}" in {path} is not an object; fix or remove it, then retry.')
    return section


def _merge_hooks(settings: dict[str, Any], bin_dir: Path, path: Path) -> None:
    hooks = _section(settings, "hooks", path)
    for event, groups in _hook_groups(bin_dir).items():
        existing = hooks.get(event, [])
        if not isinstance(existing, list) or not all(isinstance(g, dict) for g in existing):
            raise InstallError(
                f'hooks "{event}" in {path} is not a list of groups; fix it, then retry.'
            )
        kept = [g for g in existing if not _is_ours(g)]  # replaces an old install
        hooks[event] = kept + groups


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text() or "{}")
    except ValueError as exc:
        raise InstallError(
            f"{path} is not valid JSON ({exc}); fix or remove it, then retry."
        ) from exc
    if not isinstance(data, dict):
        raise InstallError(f"{path} does not hold a JSON object; fix or remove it, then retry.")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def _instructions(workspace: Path, graph: str, falkordb_mcp: bool) -> str:
    roles = "\n".join(f"     HANDOFF_ROLE={r} claude" for r in ("frontend", "backend", "deploy"))
    extra = (
        "\nFalkorDB's own MCP server (read-only) runs through npx, which needs Node 18+."
        if falkordb_mcp
        else ""
    )
    return (
        f"handoff is set up in {workspace}, on its own graph {graph}.\n\n"
        "1. FalkorDB must be running (handoff init starts it).\n"
        f"2. Open one terminal per role in {workspace} and start Claude Code with it:\n"
        f"{roles}\n"
        "   Claude Code asks once to approve the project's MCP servers.\n"
        f"3. See the graph at http://localhost:3000 (graph {graph}).\n"
        "4. Optional, a knowledge graph of the work (needs the 'knowledge' extra), from this\n"
        "   folder:  handoff knowledge"
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
    _merge_hooks(settings, bin_dir, settings_path)
    env = _section(settings, "env", settings_path)
    if graph:
        env["HANDOFF_GRAPH"] = graph
    env.setdefault("HANDOFF_GRAPH", graph_for_workspace(workspace))
    _write_json(settings_path, settings)

    mcp_path = workspace / ".mcp.json"
    mcp = _read_json(mcp_path)
    servers = _section(mcp, "mcpServers", mcp_path)
    servers["handoff"] = handoff_server_entry(str(bin_dir / "handoff-mcp"), env["HANDOFF_GRAPH"])
    if falkordb_mcp:
        servers["falkordb"] = falkordb_server_entry(config)
    else:
        servers.pop("falkordb", None)
    _write_json(mcp_path, mcp)
    return _instructions(workspace, env["HANDOFF_GRAPH"], falkordb_mcp)
