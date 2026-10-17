"""`handoff`: the command people run. Today it has one subcommand, `install`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from handoff.config import Config
from handoff.install import install


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the subcommand. Returns the exit code."""
    parser = argparse.ArgumentParser(prog="handoff")
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("install", help="set up a workspace for handoff")
    setup.add_argument("workspace", type=Path, help="the project folder the sessions work in")
    setup.add_argument(
        "--no-falkordb-mcp",
        action="store_true",
        help="leave out FalkorDB's own (read-only) MCP server",
    )
    args = parser.parse_args(argv)
    workspace = args.workspace.expanduser().resolve()
    if not workspace.is_dir():
        print(f"{workspace} is not a folder.", file=sys.stderr)
        return 1
    print(
        install(
            workspace,
            bin_dir=Path(sys.executable).parent,
            config=Config.from_env(),
            falkordb_mcp=not args.no_falkordb_mcp,
        )
    )
    return 0
