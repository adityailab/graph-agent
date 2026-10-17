"""`handoff watch`: a live view of what the sessions are doing, refreshed every 2 seconds."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from handoff.config import Config
from handoff.graph.connection import connect, graph_exists
from handoff.graph.feed import FeedEvent, recent_events
from handoff.graph.insights import current_insights
from handoff.graph.records import InsightView, SessionInfo
from handoff.graph.sessions import active_sessions
from handoff.ids import now_ms
from handoff.workspace import workspace_config

INTERVAL = 2.0
CLEAR, BOLD, DIM, RESET = "\x1b[2J\x1b[H", "\x1b[1m", "\x1b[2m", "\x1b[0m"
_COLOURS = {
    "frontend": "\x1b[36m",
    "backend": "\x1b[35m",
    "deploy": "\x1b[33m",
    "person": "\x1b[32m",
}
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


@dataclass(frozen=True)
class Frame:
    graph: str
    sessions: list[SessionInfo]
    events: list[FeedEvent]
    insights: list[InsightView]


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("watch", help="a live feed of the sessions' work (Ctrl-C to stop)")
    p.set_defaults(run=run)


def _role(role: str) -> str:
    return f"{_COLOURS.get(role, chr(27) + '[34m')}{role}{RESET}"


def _clock(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).strftime("%H:%M:%S")


def _fit(line: str, width: int) -> str:
    """Cut a line to `width` visible characters, keeping its colour codes intact."""
    if len(_ANSI.sub("", line)) <= width:
        return line
    out, seen = [], 0
    for part in re.split(f"({_ANSI.pattern})", line):
        if _ANSI.fullmatch(part):
            out.append(part)
        else:
            out.append(part[: max(0, width - 1 - seen)])
            seen += len(out[-1])
    return "".join(out) + "…" + RESET


def render_frame(frame: Frame, width: int) -> str:
    """One screen: who is active, what just happened, and what matters now."""
    who = "  ".join(
        f"{_role(s.role)} {DIM}seen {_clock(s.last_seen_at)}{RESET}" for s in frame.sessions
    )
    lines = [
        f"{BOLD}handoff watch{RESET} · graph {frame.graph} · {DIM}{datetime.now():%H:%M:%S}{RESET}",
        f"sessions: {who or 'waiting for the first session'}",
        "",
    ]
    lines += [
        f"{DIM}{_clock(e.at)}{RESET} {_role(e.role)} {BOLD}{e.kind:<14}{RESET} "
        f"{' '.join(e.text.split())}"
        for e in frame.events
    ]
    if frame.insights:
        lines += ["", f"{BOLD}What matters now{RESET}"] + [f"- {i.text}" for i in frame.insights]
    return "\n".join(_fit(line, width) for line in lines)


def watch_loop(
    fetch: Callable[[], Frame],
    write: Callable[[str], None],
    *,
    sleep: Callable[[float], None],
    frames: int | None,
    width: int,
) -> int:
    """Draw frames until Ctrl-C (or `frames` frames). Survives the database going away."""
    drawn = 0
    try:
        while frames is None or drawn < frames:
            try:
                text = render_frame(fetch(), width)
            except (RedisConnectionError, RedisTimeoutError, OSError):
                text = "database unreachable: retrying every 2 s (handoff init starts it)"
            write(CLEAR + text)
            drawn += 1
            if frames is None or drawn < frames:
                sleep(INTERVAL)
    except KeyboardInterrupt:
        write("\n")
    return 0


def _fetcher(config: Config, rows: int) -> Callable[[], Frame]:
    def fetch() -> Frame:
        if not graph_exists(config):
            return Frame(config.graph_name, [], [], [])
        graph = connect(config)
        sessions = active_sessions(graph, since=now_ms() - 24 * 60 * 60_000)
        return Frame(
            config.graph_name,
            sessions,
            recent_events(graph, limit=rows),
            current_insights(graph, limit=3),
        )

    return fetch


def run(args: argparse.Namespace) -> int:
    """Watch this folder's graph until Ctrl-C."""
    size = shutil.get_terminal_size((100, 30))
    config = workspace_config(Path.cwd(), os.environ)
    return watch_loop(
        _fetcher(config, max(5, size.lines - 10)),
        lambda text: print(text, flush=True, file=sys.stdout),
        sleep=time.sleep,
        frames=None,
        width=size.columns,
    )
