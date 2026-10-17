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
    assert first.text == "Decided: read avatarUrl. Reason: server owns urls."
    second = claim_next(ready, now=100, stale_ms=50)
    assert second is not None
    assert (second.id, second.text) == ("p1", "show avatar")
    assert claim_next(ready, now=100, stale_ms=50) is None


def test_ingested_items_are_never_claimed_again(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="x", at=10)
    item = claim_next(ready, now=100, stale_ms=50)
    assert item is not None
    mark_ingested(ready, item, at=101)
    assert claim_next(ready, now=1_000, stale_ms=50) is None


def test_a_stale_claim_is_retried(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="x", at=10)
    assert claim_next(ready, now=100, stale_ms=50) is not None
    assert claim_next(ready, now=120, stale_ms=50) is None  # still claimed
    retried = claim_next(ready, now=200, stale_ms=50)  # the first claimant died
    assert retried is not None
    assert retried.id == "p1"


def test_an_item_that_keeps_failing_is_given_up_after_five_tries(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="x", at=10)
    now = 100
    for _ in range(5):
        item = claim_next(ready, now=now, stale_ms=50)
        assert item is not None
        now += 50 * 32  # past any backoff
    assert claim_next(ready, now=now, stale_ms=50) is None


def test_retries_back_off(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="x", at=10)
    assert claim_next(ready, now=100, stale_ms=50) is not None  # next try after 150
    assert claim_next(ready, now=160, stale_ms=50) is not None  # next after 160 + 100
    assert claim_next(ready, now=230, stale_ms=50) is None  # still backing off


def test_claim_carries_the_label_and_original_length(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="yes", at=10)
    item = claim_next(ready, now=100, stale_ms=50)
    assert item is not None
    assert (item.label, item.size) == ("Request", 3)


def test_an_ingested_item_keeps_no_retry_time(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="x", at=10)
    item = claim_next(ready, now=100, stale_ms=50)
    assert item is not None
    mark_ingested(ready, item, at=101)
    rows = ready.query("MATCH (r:Request {id: 'p1'}) RETURN r.kg_retry_at, r.kg_at").result_set
    assert rows == [[None, 101]]
