"""What the person can say into the graph themselves: a message or a need for a role.

The CLI (`handoff send`) and the dashboard's command field both speak through here, so the
person is one participant with one session per folder, however they type.
"""

from __future__ import annotations

from pathlib import Path

from falkordb import Graph

from handoff.config import normalise_role
from handoff.graph.messages import add_message
from handoff.graph.needs import add_need
from handoff.graph.requests import add_request
from handoff.graph.sessions import active_sessions, upsert_session
from handoff.ids import new_id, person_session_id
from handoff.redact import redact

PERSON = "person"


def _person(graph: Graph, folder: Path, at: int) -> str:
    """Make sure the person's session for this folder exists and return its id."""
    me = person_session_id(str(folder.resolve()))
    upsert_session(graph, session_id=me, role=PERSON, cwd=str(folder.resolve()), at=at)
    return me


def send_message(graph: Graph, folder: Path, role: str, text: str, *, at: int) -> bool:
    """Message every session with `role`. True if one exists now; if not, it is kept for the
    first one that starts."""
    role = normalise_role(role)
    add_message(
        graph,
        message_id=new_id(),
        from_session_id=_person(graph, folder, at),
        to_role=role,
        kind="message",
        text=redact(text),
        reply_to=None,
        at=at,
    )
    return any(s.role == role for s in active_sessions(graph, since=0, include_person=True))


def raise_need(graph: Graph, folder: Path, role: str, text: str, *, at: int) -> str:
    """Record that the person needs something from `role`; returns the need's id. A need hangs
    off a request, so the person's words become one too."""
    me, request_id, need_id = _person(graph, folder, at), new_id(), new_id()
    clean = redact(text)
    add_request(graph, session_id=me, request_id=request_id, text=clean, at=at)
    add_need(
        graph,
        request_id=request_id,
        need_id=need_id,
        text=clean,
        for_role=normalise_role(role),
        at=at,
    )
    return need_id
