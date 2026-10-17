"""`handoff doctor`: what is wrong with this folder's setup, if anything."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from handoff.cli.style import stdout_palette
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


@dataclass(frozen=True)
class Check:
    """One thing doctor looks at: what it is, whether it is fine, and what to do if not."""

    label: str
    ok: bool
    problem: str = ""
    optional: bool = False  # worth saying, but does not make doctor fail


def checks(folder: Path, config: Config) -> list[Check]:
    """Every check for this folder, healthy or not."""
    hooks = _json(folder / ".claude" / "settings.local.json").get("hooks")
    servers = _json(folder / ".mcp.json").get("mcpServers")
    has_hooks = "handoff-hook" in json.dumps(hooks)
    has_server = isinstance(servers, dict) and "handoff" in servers
    return [
        Check(
            "hooks installed",
            has_hooks,
            f"hooks are not installed in {folder}: run handoff init there.",
        ),
        Check(
            ".mcp.json lists the handoff server",
            has_server,
            ".mcp.json has no handoff server: run handoff init.",
        ),
        Check(
            f"FalkorDB answers at {config.host}:{config.port}",
            server_reachable(config),
            f"FalkorDB does not answer at {config.host}:{config.port}: run handoff init.",
        ),
        Check(
            "claude command found",
            shutil.which("claude") is not None,
            "claude is not on PATH: install Claude Code.",
            optional=True,
        ),
        Check(
            "tmux found (handoff demo uses it)",
            shutil.which("tmux") is not None,
            "tmux is not installed: handoff demo falls back to the text version.",
            optional=True,
        ),
    ]


def findings(folder: Path, config: Config) -> list[str]:
    """Problems with this folder's setup, each with what to do; empty when healthy."""
    found = [c.problem for c in checks(folder, config) if not c.ok and not c.optional]
    return found + _recent_hook_errors(config.home)


def run(args: argparse.Namespace) -> int:
    """Print each check (exit 1 if one that matters fails)."""
    p, folder = stdout_palette(), Path.cwd()
    config = workspace_config(folder, os.environ)
    for c in checks(folder, config):
        if c.ok:
            print(f"{p.green('ok')}  {c.label}")
        elif c.optional:
            print(f"{p.amber('--')}  {c.problem}")
        else:
            print(f"{p.red('!!')}  {c.problem}")
    errors = _recent_hook_errors(config.home)
    for error in errors:
        print(f"{p.red('!!')}  {error}")
    found = findings(folder, config)
    if not found:
        print(p.green("All good: hooks, servers and database are in place."))
    return 1 if found else 0
