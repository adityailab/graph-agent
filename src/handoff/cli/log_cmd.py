"""`handoff log [role]`: what each role was asked, decided, changed and needs."""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from handoff.cli.style import Palette, stdout_palette
from handoff.config import normalise_role
from handoff.format import render_handoff, select_requests
from handoff.graph.connection import connect, graph_exists
from handoff.graph.history import handoff_requests
from handoff.ids import now_ms
from handoff.workspace import workspace_config


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("log", help="the handoff: what each role asked, decided and needs")
    p.add_argument("role", nargs="?", help="one role (default: every role)")
    p.add_argument("--hours", type=float, default=24, help="how far back (default 24)")
    p.add_argument("--limit", type=int, default=20, help="most requests to show (default 20)")
    p.set_defaults(run=run)


def _painter(p: Palette) -> Callable[[str, str], str]:
    """Colour for each part of the handoff, as the terminal sees it."""
    by_kind = {
        "role": lambda text: p.bold(p.purple(text)),
        "decided": p.green,
        "why": p.dim,
        "changed": p.blue,
        "need": p.red,
        "open": p.red,
        "resolved": p.green,
    }
    return lambda kind, text: by_kind.get(kind, p.dim)(text)


def run(args: argparse.Namespace) -> int:
    """Print the handoff. Reading it as a person records nothing in the graph."""
    config = workspace_config(Path.cwd(), os.environ)
    if not graph_exists(config):
        print("No work recorded yet in this folder's graph.")
        return 0
    role = normalise_role(args.role) if args.role else None
    since = now_ms() - int(args.hours * 60 * 60_000)
    requests = handoff_requests(connect(config), role=role, since=since)
    chosen = select_requests(requests, max(1, args.limit))
    print(render_handoff(chosen, paint=_painter(stdout_palette())))
    return 0
