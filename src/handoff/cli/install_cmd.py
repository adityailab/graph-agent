"""`handoff install <folder>`: hooks and MCP servers only, for scripting."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from handoff.config import Config
from handoff.install import InstallError, install


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("install", help="set up hooks and MCP servers in a folder")
    p.add_argument("workspace", type=Path, help="the project folder the sessions work in")
    p.add_argument(
        "--no-falkordb-mcp", action="store_true", help="leave out FalkorDB's read-only server"
    )
    p.add_argument("--graph", help="graph name to use (default: one for this folder)")
    p.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Install into the folder and print what to do next."""
    workspace = args.workspace.expanduser().resolve()
    if not workspace.is_dir():
        print(f"{workspace} is not a folder.", file=sys.stderr)
        return 1
    try:
        text = install(
            workspace,
            bin_dir=Path(sys.executable).parent,
            config=Config.from_env(),
            falkordb_mcp=not args.no_falkordb_mcp,
            graph=args.graph,
            default_graph=os.environ.get("HANDOFF_GRAPH") or None,
        )
    except InstallError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(text)
    return 0
