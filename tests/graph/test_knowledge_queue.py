from __future__ import annotations

from falkordb import Graph

from handoff.graph.decisions import add_decision
from handoff.graph.knowledge_queue import claim_next, mark_ingested
from handoff.graph.requests import add_request


def test_decisions_are_claimed_before_requests_oldest_first(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="show avatar", at=10)
    add_decision(
        ready,
        request_id="p1",
        decision_id="d1",
        text="read avatarUrl",
        reason="server owns urls",
        topic="profile",
        at=11,
    )
    first = claim_next(ready, now=100, stale_ms=50)
    assert first is not None
    assert (first.id, first.role) == ("d1", "frontend")
    assert first.text == "The frontend session decided: read avatarUrl. Reason: server owns urls."
    second = claim_next(ready, now=100, stale_ms=50)
    assert second is not None
    assert (second.id, second.text) == ("p1", 'The frontend session was asked: "show avatar"')
    assert claim_next(ready, now=100, stale_ms=50) is None


def test_ingested_items_are_never_claimed_again(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="x", at=10)
    item = claim_next(ready, now=100, stale_ms=50)
    assert item is not None
    mark_ingested(ready, item.id, at=101)
    assert claim_next(ready, now=1_000, stale_ms=50) is None


def test_a_stale_claim_is_retried(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="x", at=10)
    assert claim_next(ready, now=100, stale_ms=50) is not None
    assert claim_next(ready, now=120, stale_ms=50) is None  # still claimed
    retried = claim_next(ready, now=200, stale_ms=50)  # the first claimant died
    assert retried is not None
    assert retried.id == "p1"
