from __future__ import annotations

import pytest
from falkordb import Graph

from handoff.graph.requests import add_request, latest_request_id


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
