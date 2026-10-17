"""`handoff conventions`: the team's standing rules, which every session of a role is told."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from handoff.config import normalise_role
from handoff.format import render_conventions
from handoff.graph import conventions as store
from handoff.graph.connection import connect
from handoff.graph.schema import ensure_schema
from handoff.ids import new_id, now_ms
from handoff.redact import redact
from handoff.workspace import workspace_config

PERSON = "person"


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("conventions", help="standing rules every session is told about")
    sub = p.add_subparsers(dest="action", metavar="[add|retire]")
    add = sub.add_parser("add", help="add a rule")
    add.add_argument("rule", help="the rule, in one sentence")
    add.add_argument("--why", required=True, help="why the team follows it")
    add.add_argument("--role", default=store.ALL, help="one role (default: everyone)")
    retire = sub.add_parser("retire", help="stop a rule applying")
    retire.add_argument("id", help="the id shown in the list")
    p.add_argument("--role", default=None, help="list the rules for one role (default: all)")
    p.set_defaults(run=run)


def _list(graph: Any, role: str | None) -> int:
    rules = store.conventions_for(graph, role) if role else store.all_conventions(graph)
    print(render_conventions(rules) if rules else "No conventions are in force.")
    return 0


def run(args: argparse.Namespace) -> int:
    """List, add or retire a rule."""
    graph = connect(workspace_config(Path.cwd(), os.environ))
    ensure_schema(graph)
    if args.action == "add":
        rule_id = new_id()
        store.add_convention(
            graph,
            convention_id=rule_id,
            text=redact(args.rule.strip()),
            reason=redact(args.why.strip()),
            scope=normalise_role(args.role),
            author=PERSON,
            at=now_ms(),
        )
        print(f"Recorded convention {rule_id}.")
        return 0
    if args.action == "retire":
        done = store.retire_convention(graph, args.id, at=now_ms())
        print(f"Convention {args.id} is retired." if done else f"No convention with id {args.id}.")
        return 0 if done else 1
    return _list(graph, normalise_role(args.role) if args.role else None)
