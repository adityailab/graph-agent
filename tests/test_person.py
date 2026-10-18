from __future__ import annotations

from pathlib import Path

from falkordb import Graph

from handoff.graph.messages import claim_pending_messages
from handoff.graph.needs import open_needs
from handoff.graph.schema import ensure_schema
from handoff.graph.sessions import upsert_session
from handoff.person import raise_need, send_message


def test_a_message_from_the_person_reaches_a_session_of_that_role(
    graph: Graph, tmp_path: Path
) -> None:
    ensure_schema(graph)
    upsert_session(graph, session_id="be", role="backend", cwd=str(tmp_path), at=1)
    assert send_message(graph, tmp_path, "backend", "prices are in paise", at=5) is True
    got = claim_pending_messages(graph, session_id="be", role="backend", since=0, at=10**15)
    assert [(m.from_role, m.text) for m in got] == [("person", "prices are in paise")]


def test_a_message_to_a_role_nobody_has_yet_is_kept_and_reported(
    graph: Graph, tmp_path: Path
) -> None:
    ensure_schema(graph)
    assert send_message(graph, tmp_path, "deploy", "ship after lunch", at=5) is False
    upsert_session(graph, session_id="d1", role="deploy", cwd=str(tmp_path), at=6)
    got = claim_pending_messages(graph, session_id="d1", role="deploy", since=0, at=10**15)
    assert [m.text for m in got] == ["ship after lunch"]


def test_a_need_from_the_person_is_open_for_that_role(graph: Graph, tmp_path: Path) -> None:
    ensure_schema(graph)
    upsert_session(graph, session_id="be", role="backend", cwd=str(tmp_path), at=1)
    raise_need(graph, tmp_path, "backend", "expose avatarUrl on /me", at=5)
    raise_need(graph, tmp_path, "backend", "and a second thing", at=6)
    assert [(who, text) for _, who, text in open_needs(graph, "backend")] == [
        ("person", "expose avatarUrl on /me"),
        ("person", "and a second thing"),
    ]
