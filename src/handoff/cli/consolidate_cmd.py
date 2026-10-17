"""`handoff consolidate`: tidy the memory over time. Links decisions that different roles made
near-identically, and folds knowledge-graph concepts that differ only in case or punctuation."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from handoff.config import Config, knowledge_graph_name
from handoff.graph.agreements import link_all_agreements
from handoff.graph.connection import connect, graph_exists
from handoff.graph.knowledge import merge_same_name_entities
from handoff.workspace import workspace_config


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser(
        "consolidate", help="link agreeing decisions and fold duplicate concepts"
    )
    p.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Consolidate this folder's graph and its knowledge graph; print what changed."""
    config = workspace_config(Path.cwd(), os.environ)
    if not graph_exists(config):
        print("No work recorded yet in this folder's graph.")
        return 0
    linked = link_all_agreements(connect(config))
    print(f"Linked {linked} new pair(s) of decisions that different roles made near-identically.")
    kg_config = Config(config.host, config.port, knowledge_graph_name(config), config.home)
    if graph_exists(kg_config):
        folded = merge_same_name_entities(connect(kg_config))
        print(f"Folded {folded} duplicate concept(s) in the knowledge graph.")
    return 0
