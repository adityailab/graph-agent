from __future__ import annotations

from falkordb import Graph

from handoff.graph.consultations import add_consultations


def _consulted(graph: Graph, request_id: str) -> list[str]:
    rows = graph.query(
        "MATCH (:Request {id: $id})-[:CONSULTED]->(c:Request) RETURN c.id ORDER BY c.id",
        {"id": request_id},
    ).result_set
    return [row[0] for row in rows]


def test_reading_another_sessions_work_is_recorded(two_sessions: Graph) -> None:
    add_consultations(two_sessions, request_id="p3", consulted_ids=["p1", "p2"], at=300)
    assert _consulted(two_sessions, "p3") == ["p1", "p2"]


def test_a_sessions_own_requests_are_not_consultations(two_sessions: Graph) -> None:
    add_consultations(two_sessions, request_id="p2", consulted_ids=["p1", "p3"], at=300)
    assert _consulted(two_sessions, "p2") == ["p3"]


def test_reading_again_adds_no_second_edge(two_sessions: Graph) -> None:
    for at in (300, 400):
        add_consultations(two_sessions, request_id="p3", consulted_ids=["p1"], at=at)
    rows = two_sessions.query("MATCH ()-[k:CONSULTED]->() RETURN count(k), min(k.at)").result_set
    assert rows == [[1, 300]]
