from __future__ import annotations

from falkordb import Graph

from handoff.graph.sessions import upsert_session


def test_session_is_created_then_refreshed(graph: Graph) -> None:
    upsert_session(graph, session_id="s1", role="frontend", cwd="/w", at=1000)
    upsert_session(graph, session_id="s1", role="web", cwd="/w", at=2000)
    rows = graph.query(
        "MATCH (s:Session {id: 's1'}) RETURN s.role, s.started_at, s.last_seen_at"
    ).result_set
    assert rows == [["web", 1000, 2000]]
