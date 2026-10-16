from __future__ import annotations

from falkordb import Graph

from handoff.graph.decisions import add_decision
from handoff.graph.edits import add_edit
from handoff.graph.needs import add_need, resolve_need
from handoff.graph.paths import connection_path
from handoff.graph.requests import add_request
from handoff.graph.sessions import upsert_session


def test_path_through_a_shared_file(ready: Graph) -> None:
    upsert_session(ready, session_id="be", role="backend", cwd="/w", at=1)
    add_request(ready, session_id="s1", request_id="p1", text="add avatar", at=10)
    add_edit(ready, request_id="p1", edit_id="e1", tool="Edit", path="Card.tsx", summary="", at=11)
    add_request(ready, session_id="be", request_id="p2", text="rename field", at=20)
    add_edit(ready, request_id="p2", edit_id="e2", tool="Edit", path="Card.tsx", summary="", at=21)
    steps = connection_path(ready, from_request="p1", to_role="backend")
    assert steps is not None
    assert [s.label for s in steps] == ["Request", "Edit", "File", "Edit", "Request"]
    assert steps[2].text == "Card.tsx"
    assert steps[-1].text == "rename field"


def test_path_through_a_resolved_need_is_preferred_when_shorter(ready: Graph) -> None:
    upsert_session(ready, session_id="be", role="backend", cwd="/w", at=1)
    add_request(ready, session_id="s1", request_id="p1", text="add avatar", at=10)
    add_need(
        ready, request_id="p1", need_id="n1", text="return avatarUrl", for_role="backend", at=11
    )
    add_request(ready, session_id="be", request_id="p2", text="add avatarUrl", at=20)
    resolve_need(ready, need_id="n1", request_id="p2")
    steps = connection_path(ready, from_request="p1", to_role="backend")
    assert steps is not None
    assert [s.label for s in steps] == ["Request", "Need", "Request"]
    assert [s.via for s in steps[1:]] == ["RAISED", "RESOLVED_BY"]


def test_unconnected_work_has_no_path(ready: Graph) -> None:
    upsert_session(ready, session_id="be", role="backend", cwd="/w", at=1)
    add_request(ready, session_id="s1", request_id="p1", text="add avatar", at=10)
    add_decision(ready, request_id="p1", decision_id="d1", text="t", reason="r", topic="ui", at=11)
    add_request(ready, session_id="be", request_id="p2", text="rate limits", at=20)
    assert connection_path(ready, from_request="p1", to_role="backend") is None
