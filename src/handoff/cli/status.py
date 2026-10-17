"""`handoff status`: is it working, who is active, and what is waiting."""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from handoff.config import Config
from handoff.format import shorten
from handoff.graph.connection import connect, graph_exists, server_reachable
from handoff.graph.needs import count_open_needs
from handoff.graph.requests import latest_request_id, request_text
from handoff.graph.sessions import active_sessions
from handoff.ids import now_ms
from handoff.knowledge.lead import is_leading
from handoff.workspace import workspace_config

DAY_MS = 24 * 60 * 60_000


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("status", help="database, sessions and open needs for this folder")
    p.set_defaults(run=run)


def _sessions(config: Config) -> list[str]:
    graph = connect(config)
    lines, roles = [], []
    for s in active_sessions(graph, since=now_ms() - DAY_MS):
        request_id = latest_request_id(graph, s.id)
        text = request_text(graph, request_id) if request_id else None
        seen = datetime.fromtimestamp(s.last_seen_at / 1000).strftime("%H:%M")
        work = f'working on "{shorten(text, 70)}"' if text else "no request yet"
        lines.append(f"  {s.role:<10} seen {seen}  {work}")
        roles.append(s.role)
    counts = {r: count_open_needs(graph, r) for r in dict.fromkeys(roles)}
    needs = [f"{r}: {n} open need{'' if n == 1 else 's'}" for r, n in counts.items()]
    return [*lines, "open needs: " + (" · ".join(needs) or "none")]


def run(args: argparse.Namespace) -> int:
    """Print the state of this folder's handoff."""
    config = workspace_config(Path.cwd(), os.environ)
    if not server_reachable(config):
        print(f"FalkorDB does not answer at {config.host}:{config.port}; run handoff init.")
        return 1
    print(f"graph {config.graph_name} on FalkorDB {config.host}:{config.port}")
    print("browse it: http://localhost:3000")
    print(f"knowledge worker: {'running' if is_leading(config) else 'not running'}")
    if not graph_exists(config):
        print("No work recorded yet: start a Claude Code session in this folder.")
        return 0
    print("sessions seen in the last 24 hours:")
    print("\n".join(_sessions(config)))
    return 0
