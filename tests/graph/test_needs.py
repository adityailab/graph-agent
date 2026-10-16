from __future__ import annotations

from falkordb import Graph

from handoff.graph.needs import add_need, resolve_need
from handoff.graph.requests import add_request
from handoff.graph.sessions import upsert_session


def test_need_starts_open_and_is_resolved_by_another_request(ready: Graph) -> None:
    upsert_session(ready, session_id="s2", role="backend", cwd="/w", at=1)
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    add_request(ready, session_id="s2", request_id="p9", text="pick up", at=5)
    assert add_need(
        ready, request_id="p1", need_id="n1", text="return avatarUrl", for_role="backend", at=2
    )
    assert ready.query("MATCH (n:Need {id: 'n1'}) RETURN n.status").result_set == [["open"]]

    assert resolve_need(ready, need_id="n1", request_id="p9")
    rows = ready.query(
        "MATCH (n:Need {id: 'n1'})-[:RESOLVED_BY]->(r:Request) RETURN n.status, r.id"
    ).result_set
    assert rows == [["resolved", "p9"]]


def test_need_for_unknown_request_is_refused(ready: Graph) -> None:
    assert not add_need(ready, request_id="nope", need_id="n1", text="t", for_role="x", at=1)


def test_resolving_unknown_need_is_refused(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    assert not resolve_need(ready, need_id="nope", request_id="p1")
