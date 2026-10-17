"""`handoff dashboard`: mission control in the browser (orchestration, hand-offs, graph, tracks)."""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from collections.abc import Callable
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from handoff.config import Config
from handoff.dashboard.server import make_server
from handoff.workspace import workspace_config

DEFAULT_PORT = 8765


class DashboardError(Exception):
    """The dashboard could not start; the message says what to do."""


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("dashboard", help="mission control: the sessions, live, in a browser")
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"default {DEFAULT_PORT}")
    p.add_argument("--no-open", action="store_true", help="do not open the browser")
    p.set_defaults(run=run)


def start(
    config: Config, *, port: int, open_page: Callable[[str], object] | None
) -> ThreadingHTTPServer:
    """Bind the server (localhost only) and open the page; the caller serves it."""
    try:
        server = make_server(config, port=port)
    except OSError as exc:  # the one thing we can explain: something already has the port
        raise DashboardError(
            f"port {port} is already in use: pick another with handoff dashboard --port N"
        ) from exc
    if open_page is not None:
        open_page(f"http://127.0.0.1:{server.server_address[1]}/")
    return server


def run(args: argparse.Namespace) -> int:
    """Serve this folder's graph until Ctrl-C."""
    config = workspace_config(Path.cwd(), os.environ)
    try:
        server = start(config, port=args.port, open_page=None if args.no_open else webbrowser.open)
    except DashboardError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        f"handoff dashboard for graph {config.graph_name}: "
        f"http://127.0.0.1:{server.server_address[1]}/  (Ctrl-C to stop)",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
