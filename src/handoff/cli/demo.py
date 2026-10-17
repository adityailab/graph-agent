"""`handoff demo`: the proof. Three Claude Code sessions collaborate in a scratch project
through handoff, then the result is checked and left in FalkorDB to browse."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from handoff.cli.runner import run_command
from handoff.config import Config, knowledge_graph_name
from handoff.demo.check import check_graph, reset_graphs
from handoff.demo.drive import drive
from handoff.demo.headless import run_session
from handoff.demo.live import launch
from handoff.demo.scratch import NotAScratchFolder, prepare_scratch
from handoff.demo.script import HEADLESS, SHOPLITE
from handoff.demo.tmux import SESSION
from handoff.install import install

DEFAULT_GRAPH = "handoff_demo"  # namespaced: the demo deletes this graph on every run


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("demo", help="watch three sessions collaborate, then check it")
    p.add_argument(
        "--graph", default=DEFAULT_GRAPH, help=f"graph to (re)create (default: {DEFAULT_GRAPH})"
    )
    p.add_argument("--workspace", type=Path, help="scratch folder (default: a temp folder)")
    p.add_argument("--model", help="model for the sessions (default: haiku; sonnet with --live)")
    p.add_argument("--no-knowledge", action="store_true", help="skip the knowledge graph")
    p.add_argument(
        "--live",
        action="store_true",
        help="a tmux grid of three real Claude Code sessions and a live feed",
    )
    p.add_argument("--manual", action="store_true", help="with --live: type the prompts yourself")
    p.add_argument("--drive", action="store_true", help=argparse.SUPPRESS)  # background driver
    p.add_argument("--session", default=SESSION, help=argparse.SUPPRESS)
    p.set_defaults(run=run)


def _knowledge(config: Config) -> None:
    try:
        from handoff.knowledge.cli import main as knowledge_main
    except ImportError:
        print("(knowledge graph skipped: install the 'knowledge' extra)")
        return
    os.environ["HANDOFF_GRAPH"] = config.graph_name
    knowledge_main(["--once"])


def _report(config: Config) -> int:
    text, missing = check_graph(config)
    print(f"\n== what the deploy session can see\n{text}")
    if missing:
        print(f"\nFAIL: missing {', '.join(missing)}.")
        return 1
    print(
        f"\nPASS. Browse it at http://localhost:3000: graphs {config.graph_name} and "
        f"{knowledge_graph_name(config)}."
    )
    return 0


def _live(args: argparse.Namespace, config: Config, workspace: Path) -> int:
    if shutil.which("tmux") is None:
        print(
            "The live demo needs tmux: brew install tmux (macOS) or your package manager.",
            file=sys.stderr,
        )
        return 1
    reset_graphs(config)
    print(
        launch(
            args.session,
            workspace,
            config,
            run_command,
            model=args.model or "sonnet",
            manual=args.manual,
        ),
        flush=True,
    )
    if sys.stdout.isatty() and not os.environ.get("TMUX"):
        # This terminal joins the grid; tmux is found on PATH like any command the person runs.
        os.execvp("tmux", ["tmux", "attach", "-t", args.session])  # noqa: S606, S607
    return 0


def run(args: argparse.Namespace) -> int:
    """Reset the demo graph, run the sessions, build the knowledge graph, check."""
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
    base = Config.from_env()
    config = Config(base.host, base.port, args.graph, base.home)
    workspace = (args.workspace or Path(tempfile.gettempdir()) / "handoff-demo").resolve()
    try:
        prepare_scratch(workspace)
    except NotAScratchFolder as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.live:
        return _live(args, config, workspace)
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
        _knowledge(config)
    return _report(config)
