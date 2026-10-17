"""`handoff coordinator`: the always-on agent that nudges sessions within set rules."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

from handoff.config import Config
from handoff.coordinator.rules import Action, Thresholds, run_rules
from handoff.coordinator.runner import Coordinator
from handoff.graph.connection import connect, graph_exists, server_reachable
from handoff.graph.schema import ensure_schema
from handoff.ids import now_ms
from handoff.knowledge.lead import lock_name
from handoff.workspace import workspace_config


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("coordinator", help="always-on agent: reminders, heads-ups, digests")
    p.add_argument("--once", action="store_true", help="one pass, then exit")
    p.add_argument("--dry-run", action="store_true", help="say what it would send; send nothing")
    p.add_argument(
        "--stale-minutes", type=int, default=30, help="remind about needs open this long"
    )
    p.add_argument(
        "--collision-minutes",
        type=int,
        default=60,
        help="warn when two roles changed one file within this time",
    )
    p.add_argument("--digest-minutes", type=int, default=60, help="digest interval (0 = none)")
    p.set_defaults(run=run)


def _show(actions: list[Action], *, dry_run: bool) -> None:
    verb = "would send to" if dry_run else "sent to"
    for a in actions:
        print(f"[{a.rule}] {verb} {', '.join(a.to_roles)}: {a.text.splitlines()[0]}")
    if not actions:
        print("Nothing to do.")


def run(args: argparse.Namespace) -> int:
    """One pass (--once) or run until Ctrl-C, as this graph's single coordinator."""
    config = workspace_config(Path.cwd(), os.environ)
    if not server_reachable(config) or not graph_exists(config):
        print("No graph to watch yet: run handoff init and start a session.", file=sys.stderr)
        return 1
    graph = connect(config)
    ensure_schema(graph)
    thresholds = Thresholds(args.stale_minutes, args.collision_minutes, args.digest_minutes)
    if args.once:
        _show(
            run_rules(graph, now=now_ms(), thresholds=thresholds, dry_run=args.dry_run),
            dry_run=args.dry_run,
        )
        return 0
    return _serve(config, graph, thresholds, dry_run=args.dry_run)


def _serve(config: Config, graph: Any, thresholds: Thresholds, *, dry_run: bool) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
    coordinator = Coordinator(
        graph=graph,
        home=config.home,
        lock_name=lock_name(config),
        thresholds=thresholds,
        dry_run=dry_run,
    )
    if not coordinator.try_lead():
        print("Another coordinator is already running for this graph.", file=sys.stderr)
        return 1
    coordinator.stand_down()  # run() takes the lock itself
    print(f"Coordinating graph {config.graph_name} (Ctrl-C to stop).", flush=True)
    thread = coordinator.start()
    try:
        while thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        coordinator.stop()
        thread.join(timeout=5)
    return 0
