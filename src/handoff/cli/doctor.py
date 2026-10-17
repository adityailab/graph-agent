"""`handoff doctor`: what is wrong with this folder's setup, if anything."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from handoff.config import Config
from handoff.graph.connection import server_reachable
from handoff.workspace import workspace_config

RECENT_SECONDS = 3600
MAX_ERRORS = 5


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("doctor", help="check this folder's hooks, servers and database")
    p.set_defaults(run=run)


def _json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _recent_hook_errors(home: Path) -> list[str]:
    path = home / "logs" / "hooks.log"
    lines = path.read_text(errors="replace").splitlines() if path.exists() else []
    recent = []
    for line in lines:
        if " ERROR " not in line:
            continue
        try:
            when = time.mktime(time.strptime(line[:19], "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            continue
        if time.time() - when <= RECENT_SECONDS:
            recent.append(f"hook error at {line[11:16]}: {line.split(': ', 1)[-1]}")
    return recent[-MAX_ERRORS:]


def findings(folder: Path, config: Config) -> list[str]:
    """Problems with this folder's setup, each with what to do; empty when healthy."""
    found = []
    hooks = _json(folder / ".claude" / "settings.local.json").get("hooks")
    if "handoff-hook" not in json.dumps(hooks):
        found.append(f"hooks are not installed in {folder}: run handoff init there.")
    servers = _json(folder / ".mcp.json").get("mcpServers")
    if not isinstance(servers, dict) or "handoff" not in servers:
        found.append(".mcp.json has no handoff server: run handoff init.")
    if not server_reachable(config):
        found.append(f"FalkorDB does not answer at {config.host}:{config.port}: run handoff init.")
    return found + _recent_hook_errors(config.home)


def run(args: argparse.Namespace) -> int:
    """Print what is wrong (exit 1), or that all is well (exit 0)."""
    found = findings(Path.cwd(), workspace_config(Path.cwd(), os.environ))
    for item in found:
        print(f"- {item}")
    if not found:
        print("All good: hooks, servers and database are in place.")
    return 1 if found else 0
