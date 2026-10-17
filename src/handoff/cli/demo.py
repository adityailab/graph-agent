"""`handoff demo`: the proof. Three Claude Code sessions collaborate in a scratch project
through handoff, then the result is checked and left in FalkorDB to browse."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from handoff.config import Config, knowledge_graph_name
from handoff.demo.check import check_graph, reset_graphs
from handoff.demo.headless import run_session
from handoff.demo.script import HEADLESS
from handoff.install import install


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("demo", help="watch three sessions collaborate, then check it")
    p.add_argument("--graph", default="demo", help="graph to (re)create (default: demo)")
    p.add_argument("--workspace", type=Path, help="scratch folder (default: a temp folder)")
    p.add_argument("--model", default="haiku", help="model for the sessions (default: haiku)")
    p.add_argument("--no-knowledge", action="store_true", help="skip the knowledge graph")
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


def run(args: argparse.Namespace) -> int:
    """Reset the demo graph, run the sessions, build the knowledge graph, check."""
    if shutil.which("claude") is None:
        print(
            "The demo needs Claude Code (claude): see https://claude.com/claude-code.",
            file=sys.stderr,
        )
        return 1
    base = Config.from_env()
    config = Config(base.host, base.port, args.graph, base.home)
    workspace = (args.workspace or Path(tempfile.gettempdir()) / "handoff-demo").resolve()
    shutil.rmtree(workspace, ignore_errors=True)
    workspace.mkdir(parents=True)
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
        print(run_session(role, prompt, workspace, config, model=args.model), flush=True)
    if not args.no_knowledge:
        _knowledge(config)
    return _report(config)
