"""`handoff knowledge`: the knowledge worker, on this folder's graph."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from handoff.workspace import workspace_graph


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("knowledge", help="build the knowledge graph from the sessions' work")
    p.add_argument("--once", action="store_true", help="ingest what is pending, then exit")
    p.add_argument("--quiet", action="store_true", help="hide library log lines")
    p.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Run handoff-knowledge with this folder's graph (it reads HANDOFF_GRAPH)."""
    from handoff.knowledge.cli import main

    os.environ["HANDOFF_GRAPH"] = workspace_graph(Path.cwd(), os.environ)
    return main([*(["--once"] if args.once else []), *(["--quiet"] if args.quiet else [])])
