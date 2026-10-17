"""`handoff` with no command: where things stand and what to run next."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from handoff.cli.style import Palette, stdout_palette
from handoff.graph.connection import connect, graph_exists, server_reachable
from handoff.graph.needs import count_open_needs
from handoff.graph.sessions import active_sessions
from handoff.ids import now_ms
from handoff.workspace import workspace_config

DAY_MS = 24 * 60 * 60_000
GROUPS = (
    (
        "start",
        (
            ("init", "set up this folder, database included"),
            ("demo", "watch three sessions collaborate"),
            ("doctor", "check the setup"),
        ),
    ),
    (
        "watch",
        (
            ("dashboard", "mission control in the browser"),
            ("open", "jump to mission control, the graph or the guide"),
            ("watch", "a live feed in the terminal"),
            ("status", "who is active, what is open"),
            ("log", "what each role asked and decided"),
        ),
    ),
    (
        "act",
        (
            ("send", "message a session"),
            ("ask", "ask the graph a question"),
            ("insights", "what matters now"),
            ("knowledge", "build the concept graph"),
            ("coordinator", "reminders and digests"),
        ),
    ),
    ("shell", (("completion", "tab completion for bash or zsh"),)),
)


@dataclass(frozen=True)
class HomeState:
    database: bool
    sessions: int
    open_needs: int


def gather_state(folder: Path) -> HomeState:
    """A quick look at this folder's graph; never creates anything."""
    config = workspace_config(folder, dict(os.environ))
    if not server_reachable(config):
        return HomeState(False, 0, 0)
    if not graph_exists(config):
        return HomeState(True, 0, 0)
    graph = connect(config)
    sessions = active_sessions(graph, since=now_ms() - DAY_MS)
    roles = {s.role for s in sessions}
    return HomeState(True, len(sessions), sum(count_open_needs(graph, r) for r in roles))


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _next_step(state: HomeState) -> str:
    if not state.database:
        return "handoff init"
    if state.sessions:
        return "handoff dashboard"
    return "handoff demo"


def _state_line(p: Palette, state: HomeState) -> str:
    if not state.database:
        return f"{p.red('●')} database not running"
    sessions, needs = _plural(state.sessions, "session"), _plural(state.open_needs, "open need")
    return f"{p.green('●')} {sessions} in the last 24 hours, {needs}"


def render_home(p: Palette, state: HomeState) -> str:
    """The home screen as text."""
    out = [
        f"{p.green('$ handoff')}  {p.dim('parallel Claude Code sessions that share intent')}",
        _state_line(p, state),
        "",
        p.bold("# commands"),
    ]
    for title, commands in GROUPS:
        out.append(p.dim(f"  {title}"))
        out += [f"    {p.blue(f'handoff {name:<13}')}{p.dim(text)}" for name, text in commands]
    out += [
        "",
        f"next: {p.green(_next_step(state))}    {p.dim('handoff <command> --help for details')}",
    ]
    return "\n".join(out)


def show() -> int:
    """Print the home screen for the current folder."""
    print(render_home(stdout_palette(), gather_state(Path.cwd())))
    return 0
