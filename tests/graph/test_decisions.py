from __future__ import annotations

from falkordb import Graph

from handoff.graph.decisions import add_decision, normalise_topic
from handoff.graph.requests import add_request


def test_topic_names_are_normalised() -> None:
    assert normalise_topic("  Auth   Tokens ") == "auth tokens"


def test_decision_hangs_off_request_with_topic(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    assert add_decision(
        ready,
        request_id="p1",
        decision_id="d1",
        text="use fullName",
        reason="no client-side joining",
        topic="User Profile",
        at=2,
    )
    rows = ready.query(
        "MATCH (:Request {id: 'p1'})-[:LED_TO]->(d:Decision)-[:ABOUT]->(t:Topic) "
        "RETURN d.text, d.reason, t.name"
    ).result_set
    assert rows == [["use fullName", "no client-side joining", "user profile"]]


def test_decisions_on_the_same_topic_share_one_topic_node(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    for i in range(2):
        add_decision(
            ready, request_id="p1", decision_id=f"d{i}", text="t", reason="r", topic="Auth", at=2
        )
    assert ready.query("MATCH (t:Topic) RETURN count(t)").result_set == [[1]]


def test_decision_for_unknown_request_is_refused(ready: Graph) -> None:
    assert not add_decision(
        ready, request_id="nope", decision_id="d1", text="t", reason="r", topic="x", at=1
    )
