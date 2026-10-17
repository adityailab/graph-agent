"""`handoff demo`: the proof. Three Claude Code sessions collaborate in a scratch project
through handoff, then the result is checked and left in FalkorDB to browse."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
import webbrowser
from pathlib import Path
from typing import Any

from handoff.cli.runner import run_command
from handoff.config import Config
from handoff.demo.check import reset_graphs
from handoff.demo.drive import drive
from handoff.demo.finish import build_knowledge, report
from handoff.demo.headless import run_session
from handoff.demo.live import launch
from handoff.demo.mission import start_mission_control
from handoff.demo.scratch import NotAScratchFolder, prepare_scratch
from handoff.demo.script import HEADLESS, SHOPLITE
from handoff.demo.tmux import SESSION
from handoff.install import install

DASHBOARD_PORT = 8765

DEFAULT_GRAPH = "handoff_demo"  # namespaced: the demo deletes this graph on every run


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("demo", help="watch three sessions collaborate, then check it")
    p.add_argument(
        "--graph", default=DEFAULT_GRAPH, help=f"graph to (re)create (default: {DEFAULT_GRAPH})"
    )
    p.add_argument("--workspace", type=Path, help="scratch folder (default: a temp folder)")
    p.add_argument("--model", help="model for the sessions (default: haiku, the cheapest)")
    p.add_argument("--no-knowledge", action="store_true", help="skip the knowledge graph")
    p.add_argument(
        "--live",
        action="store_true",
        help="the tmux grid of three real sessions and a live feed (the default when tmux is "
        "installed and you are at a terminal)",
    )
    p.add_argument("--headless", action="store_true", help="run as plain text, without tmux")
    p.add_argument("--manual", action="store_true", help="with --live: type the prompts yourself")
    p.add_argument("--drive", action="store_true", help=argparse.SUPPRESS)  # background driver
    p.add_argument("--session", default=SESSION, help=argparse.SUPPRESS)
    p.set_defaults(run=run)


def _live(args: argparse.Namespace, config: Config, workspace: Path) -> int:
    reset_graphs(config)
    print(
        launch(
            args.session,
            workspace,
            config,
            run_command,
            model=args.model or "haiku",
            manual=args.manual,
        ),
        flush=True,
    )
    # After launch: it wrote the folder's settings, which tell the dashboard which graph to show.
    page = start_mission_control(workspace, config.home / "demo", port=DASHBOARD_PORT)
    print(f"Mission control: {page}#orchestration", flush=True)
    if _interactive():
        webbrowser.open(f"{page}#orchestration")
    if _interactive() and not os.environ.get("TMUX"):
        # This terminal joins the grid; tmux is found on PATH like any command the person runs.
        os.execvp("tmux", ["tmux", "attach", "-t", args.session])  # noqa: S606, S607
    return 0


def _interactive() -> bool:
    """True when output goes to a real terminal (the grid needs one to attach to)."""
    return sys.stdout.isatty()


def _wants_live(args: argparse.Namespace) -> bool:
    """The grid is the default; --headless forces text, --live insists on the grid, and a
    missing tmux or a piped output falls back to headless (saying so)."""
    if args.headless:
        return False
    if args.live:
        return True
    if shutil.which("tmux") is None:
        print("(tmux is not installed, so this runs headless; brew install tmux for the grid)")
        return False
    return _interactive()


def _headless(args: argparse.Namespace, config: Config, workspace: Path) -> int:
    print(
        f"handoff demo in {workspace}, graph {config.graph_name}. "
        f"This runs {len(HEADLESS)} Claude Code sessions on your plan (a few minutes).",
        flush=True,
    )
    reset_graphs(config)
    install(
        workspace,
        bin_dir=Path(sys.executable).parent,
        config=config,
        falkordb_mcp=False,
        graph=config.graph_name,
    )
    for role, prompt in HEADLESS:
        print(f"\n== {role}\n> {prompt}", flush=True)
        reply = run_session(role, prompt, workspace, config, model=args.model or "haiku")
        print(reply, flush=True)
    if not args.no_knowledge:
        build_knowledge(config)
    return report(config)


def run(args: argparse.Namespace) -> int:
    """Run the demo: the tmux grid by default, or headless (see _wants_live)."""
    if args.drive:
        return drive(
            SHOPLITE,
            session=args.session,
            runner=run_command,
            sleep=time.sleep,
            say=lambda line: print(line, flush=True),
        )
    if shutil.which("claude") is None:
        print(
            "The demo needs Claude Code (claude): see https://claude.com/claude-code.",
            file=sys.stderr,
        )
        return 1
    live = _wants_live(args)
    if args.live and shutil.which("tmux") is None:  # check before any folder is touched
        print(
            "The live demo needs tmux: brew install tmux (macOS) or your package manager. "
            "Or run handoff demo --headless, the same collaboration as text, without tmux.",
            file=sys.stderr,
        )
        return 1
    base = Config.from_env()
    config = Config(base.host, base.port, args.graph, base.home)
    workspace = (args.workspace or Path(tempfile.gettempdir()) / "handoff-demo").resolve()
    try:
        prepare_scratch(workspace)
    except NotAScratchFolder as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return _live(args, config, workspace) if live else _headless(args, config, workspace)
