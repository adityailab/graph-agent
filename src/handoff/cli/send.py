"""`handoff send <role> "text"`: the person messages a session; an idle one wakes."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from handoff.config import normalise_role
from handoff.graph.connection import connect, server_reachable
from handoff.graph.messages import add_message
from handoff.graph.schema import ensure_schema
from handoff.graph.sessions import active_sessions, upsert_session
from handoff.ids import new_id, now_ms, person_session_id
from handoff.redact import redact
from handoff.workspace import workspace_config

PERSON = "person"


def add_parser(commands: Any) -> None:
    """Register the subcommand."""
    p = commands.add_parser("send", help="send a message to the session(s) with a role")
    p.add_argument("role", help="who to tell, e.g. backend")
    p.add_argument("text", help="the message")
    p.set_defaults(run=run)


def run(args: argparse.Namespace) -> int:
    """Record the message from this folder's person session to the role."""
    folder = Path.cwd().resolve()
    config = workspace_config(folder, os.environ)
    if not server_reachable(config):
        print(
            f"FalkorDB does not answer at {config.host}:{config.port}; run handoff init.",
            file=sys.stderr,
        )
        return 1
    graph = connect(config)
    ensure_schema(graph)
    role, now, me = normalise_role(args.role), now_ms(), person_session_id(str(folder))
    upsert_session(graph, session_id=me, role=PERSON, cwd=str(folder), at=now)
    add_message(
        graph,
        message_id=new_id(),
        from_session_id=me,
        to_role=role,
        kind="message",
        text=redact(args.text),
        reply_to=None,
        at=now,
    )
    known = any(s.role == role for s in active_sessions(graph, since=0, include_person=True))
    later = f" No session has the role {role} yet; it will get this when one starts."
    print(f"Sent to {role}." + ("" if known else later))
    return 0
