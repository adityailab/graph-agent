"""Mission control for the live demo: the dashboard server, started beside the tmux grid."""

from __future__ import annotations

import sys
from pathlib import Path

from handoff.demo.background import start_detached


def start_mission_control(folder: Path, state: Path, *, port: int) -> str:
    """Serve the demo folder's graph in the background; returns the page's address. The folder
    is the working directory so the dashboard reads the demo's own graph from its settings."""
    start_detached(
        [
            str(Path(sys.executable).parent / "handoff"),
            "dashboard",
            "--no-open",
            "--port",
            str(port),
        ],
        log=state / "dashboard.log",
        pid_file=state / "dashboard.pid",
        cwd=folder,
    )
    return f"http://127.0.0.1:{port}/"
