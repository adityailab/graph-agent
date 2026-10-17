"""`handoff timeline <topic>`: how the decisions about a topic changed over time."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from handoff.format import render_timeline
from handoff.graph.connection import connect, graph_exists
from handoff.graph.decisions import normalise_topic
from handoff.graph.timeline import topic_timeline
from handoff.workspace import workspace_config


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("timeline", help="how decisions about a topic changed over time")
    p.add_argument("topic", help="the topic, e.g. profile")
    p.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Print the topic's decisions oldest first, with what replaced what."""
    config = workspace_config(Path.cwd(), os.environ)
    entries = topic_timeline(connect(config), args.topic) if graph_exists(config) else []
    if not entries:
        print(f"No decisions recorded about {args.topic.strip()}.")
        return 0
    print(render_timeline(normalise_topic(args.topic), entries))
    return 0
