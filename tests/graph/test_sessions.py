from __future__ import annotations

from falkordb import Graph

from handoff.graph.sessions import active_session, active_sessions, get_session, upsert_session


def test_session_is_created_then_refreshed(graph: Graph) -> None:
    upsert_session(graph, session_id="s1", role="frontend", cwd="/w", at=1000)
    upsert_session(graph, session_id="s1", role="web", cwd="/w", at=2000)
    rows = graph.query(
        "MATCH (s:Session {id: 's1'}) RETURN s.role, s.started_at, s.last_seen_at"
    ).result_set
    assert rows == [["web", 1000, 2000]]


def test_active_session_is_found_by_role_and_folder(two_sessions: Graph) -> None:
    session = active_session(two_sessions, role="backend", cwd="/w")
    assert session is not None
    assert session.id == "be"
    assert active_session(two_sessions, role="deploy", cwd="/w") is None


def test_active_sessions_are_filtered_by_last_seen(two_sessions: Graph) -> None:
    assert [s.role for s in active_sessions(two_sessions, since=0)] == ["backend", "frontend"]
    assert [s.role for s in active_sessions(two_sessions, since=150)] == ["backend"]


def test_session_is_found_by_its_id(two_sessions: Graph) -> None:
    session = get_session(two_sessions, "fe")
    assert session is not None
    assert session.role == "frontend"
    assert get_session(two_sessions, "nope") is None
