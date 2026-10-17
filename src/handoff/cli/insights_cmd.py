"""`handoff insights`: what FalkorDB's algorithms find important in this folder's work."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from handoff.config import Config, knowledge_graph_name
from handoff.graph.connection import connect, graph_exists
from handoff.graph.insights import current_insights, refresh_insights
from handoff.ids import now_ms
from handoff.mcp.insights_view import RECENT_MS
from handoff.workspace import workspace_config

_NONE_YET = (
    "No insights yet: they appear once sessions read each other's work, change the same "
    "files, or the knowledge graph has concepts (handoff knowledge)."
)


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("insights", help="what matters now, found by graph algorithms")
    p.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Recompute the insights and print them, most urgent first."""
    config = workspace_config(Path.cwd(), os.environ)
    if not graph_exists(config):
        print("No work recorded yet in this folder's graph.")
        return 0
    kg_config = Config(config.host, config.port, knowledge_graph_name(config), config.home)
    kg = connect(kg_config) if graph_exists(kg_config) else None
    graph = connect(config)
    now = now_ms()
    refresh_insights(graph, kg, at=now, since=now - RECENT_MS)
    insights = current_insights(graph, limit=12)
    for i in insights:
        print(f"[{i.kind}] {i.text}")
    if not insights:
        print(_NONE_YET)
    return 0
