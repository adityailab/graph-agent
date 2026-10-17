"""`handoff open [dashboard|graph|guide]`: jump to the page you want in the browser."""

from __future__ import annotations

import argparse
import os
import socket
import sys
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import quote

from handoff.workspace import workspace_config

DASHBOARD_PORT = 8765
BROWSER = "http://localhost:3000"
GUIDE = "https://github.com/adityailab/graph-agent/blob/main/docs/guide.md"


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("open", help="open mission control, the graph or the guide")
    p.add_argument(
        "target",
        nargs="?",
        default="dashboard",
        choices=("dashboard", "graph", "guide"),
        help="dashboard: mission control (default); graph: this project's graph in the "
        "FalkorDB Browser; guide: the user guide",
    )
    p.add_argument("--port", type=int, default=DASHBOARD_PORT, help="the dashboard's port")
    p.add_argument("--print", action="store_true", help="print the address instead of opening it")
    p.set_defaults(run=run)


def is_listening(host: str, port: int) -> bool:
    """Whether something accepts connections at host:port."""
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:  # nothing there (or unreachable): the answer is simply no
        return False


def _address(target: str, port: int) -> str:
    if target == "graph":
        graph = workspace_config(Path.cwd(), os.environ).graph_name
        return f"{BROWSER}/graph?graph={quote(graph)}"
    if target == "guide":
        return GUIDE
    return f"http://127.0.0.1:{port}/"


def run(args: argparse.Namespace) -> int:
    """Print or open the address; a dashboard that is not running says how to start it."""
    url = _address(args.target, args.port)
    if args.print:
        print(url)
        return 0
    if args.target == "dashboard" and not is_listening("127.0.0.1", args.port):
        print(
            "Mission control is not running here: start it with handoff dashboard.", file=sys.stderr
        )
        return 1
    webbrowser.open(url)
    print(f"Opened {url}")
    return 0
