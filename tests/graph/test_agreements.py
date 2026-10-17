from __future__ import annotations

from falkordb import Graph

from handoff.graph.agreements import link_agreements
from handoff.graph.decisions import add_decision, set_decision_embedding
from handoff.graph.schema import EMBED_DIM


def _vec(x: float, y: float) -> list[float]:
    return [x, y] + [0.0] * (EMBED_DIM - 2)


def _decide(graph: Graph, request: str, did: str, text: str, vec: list[float]) -> None:
    add_decision(
        graph, request_id=request, decision_id=did, text=text, reason="r", topic="t", at=500
    )
    set_decision_embedding(graph, did, vec)


def test_a_near_identical_decision_by_another_role_is_linked_as_agreeing(
    two_sessions: Graph,
) -> None:
    set_decision_embedding(two_sessions, "d1", _vec(1.0, 0.0))  # frontend's decision
    _decide(two_sessions, "p3", "d2", "avatar url comes from the server", _vec(0.99, 0.12))
    agreed = link_agreements(two_sessions, "d2", _vec(0.99, 0.12), role="backend", at=600)
    assert [(a.role, a.text) for a in agreed] == [("frontend", "read avatarUrl")]
    rows = two_sessions.query(
        "MATCH (:Decision {id: 'd2'})-[r:AGREES_WITH]->(:Decision {id: 'd1'}) RETURN r.at"
    ).result_set
    assert rows == [[600]]


def test_a_decision_by_the_same_role_is_not_an_agreement(two_sessions: Graph) -> None:
    set_decision_embedding(two_sessions, "d1", _vec(1.0, 0.0))
    _decide(two_sessions, "p2", "d2", "again", _vec(0.99, 0.12))  # p2 is frontend's too
    assert link_agreements(two_sessions, "d2", _vec(0.99, 0.12), role="frontend", at=600) == []


def test_a_distant_decision_is_not_an_agreement(two_sessions: Graph) -> None:
    set_decision_embedding(two_sessions, "d1", _vec(1.0, 0.0))
    _decide(two_sessions, "p3", "d2", "unrelated", _vec(0.0, 1.0))
    assert link_agreements(two_sessions, "d2", _vec(0.0, 1.0), role="backend", at=600) == []


def test_linking_twice_keeps_one_edge(two_sessions: Graph) -> None:
    set_decision_embedding(two_sessions, "d1", _vec(1.0, 0.0))
    _decide(two_sessions, "p3", "d2", "same thing", _vec(0.99, 0.12))
    for at in (600, 700):
        link_agreements(two_sessions, "d2", _vec(0.99, 0.12), role="backend", at=at)
    rows = two_sessions.query("MATCH ()-[r:AGREES_WITH]->() RETURN count(r)").result_set
    assert rows == [[1]]


def test_existing_decisions_are_linked_later_to_earlier_at_the_later_time(
    two_sessions: Graph,
) -> None:
    from handoff.graph.agreements import link_all_agreements

    set_decision_embedding(two_sessions, "d1", _vec(1.0, 0.0))  # frontend, made at 112
    _decide(two_sessions, "p3", "d2", "same thing", _vec(0.99, 0.12))  # backend, made at 500
    _decide(two_sessions, "p3", "d3", "far away", _vec(0.0, 1.0))
    assert link_all_agreements(two_sessions) == 1
    assert link_all_agreements(two_sessions) == 0  # nothing new the second time
    rows = two_sessions.query(
        "MATCH (:Decision {id: 'd2'})-[r:AGREES_WITH]->(:Decision {id: 'd1'}) RETURN r.at"
    ).result_set
    assert rows == [[500]]
