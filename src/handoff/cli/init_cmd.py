"""`handoff init [folder]`: everything a folder needs, in one command."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from handoff.cli.banner import show_banner, stdout_animated, step
from handoff.cli.runner import run_command
from handoff.database import LOCAL_HOSTS, DatabaseUnavailable, ensure_database
from handoff.graph.connection import server_reachable
from handoff.install import InstallError, install
from handoff.prereqs import check_prerequisites
from handoff.workspace import workspace_config

_DATABASE = {
    "running": "FalkorDB is already running; using it.",
    "started": "Started the existing handoff-falkordb container.",
    "created": (
        "Started FalkorDB in Docker (container handoff-falkordb, data in volume handoff-data)."
    ),
}


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("init", help="set up handoff for a project folder, database included")
    p.add_argument("folder", nargs="?", type=Path, default=Path("."), help="default: this folder")
    p.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Check prerequisites, make sure FalkorDB answers, install, and say what to do next."""
    folder = args.folder.expanduser().resolve()
    if not folder.is_dir():
        print(f"{folder} is not a folder.", file=sys.stderr)
        return 1
    config = workspace_config(folder, os.environ)
    show = stdout_animated()  # the logo and live checklist only on a real terminal
    show_banner(sys.stdout, animate=show)
    with step("checking prerequisites", sys.stdout, enabled=show) as checking:
        reachable = server_reachable(config)
        problems = check_prerequisites(
            run_command,
            which=shutil.which,
            need_docker=not reachable and config.host in LOCAL_HOSTS,
        )
        if any(not p.optional for p in problems):
            checking.fail()
    for problem in problems:
        print(f"{'note' if problem.optional else 'missing'}: {problem.fix}", file=sys.stderr)
    if any(not p.optional for p in problems):
        return 1
    try:
        with step("making sure FalkorDB runs", sys.stdout, enabled=show):
            status = ensure_database(config, run_command)
        with step("installing hooks and MCP servers", sys.stdout, enabled=show):
            text = install(
                folder,
                bin_dir=Path(sys.executable).parent,
                config=config,
                falkordb_mcp=not any(p.name == "npx" for p in problems),
                default_graph=os.environ.get("HANDOFF_GRAPH") or None,
            )
    except (DatabaseUnavailable, InstallError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(_DATABASE[status])
    print(text)
    return 0
