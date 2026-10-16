from __future__ import annotations

import pytest
from falkordb import Graph

from handoff.graph.decisions import add_decision
from handoff.graph.edits import add_edit
from handoff.graph.requests import add_request, latest_request_id, request_needs_decision


def test_requests_are_numbered_and_chained(ready: Graph) -> None:
    assert add_request(ready, session_id="s1", request_id="p1", text="one", at=1) == 1
    assert add_request(ready, session_id="s1", request_id="p2", text="two", at=2) == 2
    chain = ready.query("MATCH (a:Request)-[:NEXT]->(b:Request) RETURN a.id, b.id").result_set
    assert chain == [["p1", "p2"]]


def test_repeated_request_is_not_duplicated(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    assert add_request(ready, session_id="s1", request_id="p1", text="one", at=1) == 1
    assert ready.query("MATCH (r:Request) RETURN count(r)").result_set == [[1]]


def test_request_for_unknown_session_raises(ready: Graph) -> None:
    with pytest.raises(LookupError):
        add_request(ready, session_id="nope", request_id="p1", text="x", at=1)


def test_request_text_round_trips_exactly(ready: Graph) -> None:
    text = 'Fix "name"}) DETACH DELETE (n) // नमस्ते 🚀\nsecond line'
    add_request(ready, session_id="s1", request_id="p1", text=text, at=1)
    rows = ready.query("MATCH (r:Request {id: 'p1'}) RETURN r.text").result_set
    assert rows == [[text]]


def test_latest_request_is_the_highest_numbered(two_sessions: Graph) -> None:
    assert latest_request_id(two_sessions, "fe") == "p2"
    assert latest_request_id(two_sessions, "nobody") is None


def test_request_replayed_after_a_newer_one_is_not_the_latest(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    add_request(ready, session_id="s1", request_id="p3", text="three", at=3)
    for _ in range(2):
        add_request(ready, session_id="s1", request_id="p2", text="two", at=2)
    assert latest_request_id(ready, "s1") == "p3"
    assert ready.query("MATCH (r:Request {id: 'p2'}) RETURN count(r)").result_set == [[1]]


def test_repeated_request_adds_no_extra_links(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    for _ in range(2):
        add_request(ready, session_id="s1", request_id="p2", text="two", at=2)
    assert ready.query("MATCH ()-[n:NEXT]->() RETURN count(n)").result_set == [[1]]
    assert ready.query("MATCH ()-[x:RECEIVED]->() RETURN count(x)").result_set == [[2]]


def test_request_with_edits_and_no_decision_needs_one(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    assert not request_needs_decision(ready, "p1")
    add_edit(ready, request_id="p1", edit_id="e1", tool="Edit", path="a", summary="", at=2)
    assert request_needs_decision(ready, "p1")
    add_decision(ready, request_id="p1", decision_id="d1", text="t", reason="r", topic="x", at=3)
    assert not request_needs_decision(ready, "p1")
