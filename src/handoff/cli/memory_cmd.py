"""`handoff memory`: what the graph remembers, by kind of memory, and what each session holds."""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from handoff.cli.style import Palette, stdout_palette
from handoff.format_memory import render_memory
from handoff.graph.connection import connect, graph_exists
from handoff.graph.memory_view import concept_total, memory_types, role_contexts
from handoff.ids import now_ms
from handoff.workspace import workspace_config

DAY_MS = 24 * 60 * 60_000


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser(
        "memory", help="what is remembered, by kind, and what each session holds"
    )
    p.add_argument("--hours", type=float, default=24, help="how far back a session counts as live")
    p.set_defaults(run=run)


def _painter(p: Palette) -> Callable[[str, str], str]:
    by_kind: dict[str, Callable[[str], str]] = {
        "head": p.bold,
        "memory": lambda text: p.bold(p.teal(text)),
        "role": lambda text: p.bold(p.purple(text)),
    }
    return lambda kind, text: by_kind.get(kind, p.dim)(text)


def run(args: argparse.Namespace) -> int:
    """Print the overview for this folder's graph."""
    config = workspace_config(Path.cwd(), os.environ)
    if not graph_exists(config):
        print("No work recorded yet in this folder's graph.")
        return 0
    graph, since = connect(config), now_ms() - int(args.hours * 60 * 60_000)
    types = memory_types(graph, concepts=concept_total(config), since=since)
    print(render_memory(types, role_contexts(graph, since=since), _painter(stdout_palette())))
    return 0
