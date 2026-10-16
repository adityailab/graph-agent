from __future__ import annotations

from falkordb import Graph

from handoff.graph.edits import add_edit
from handoff.graph.overlaps import recent_edits_by_others, shared_files
from handoff.graph.requests import add_request
from handoff.graph.sessions import upsert_session


def _setup(g: Graph) -> None:
    upsert_session(g, session_id="be", role="backend", cwd="/w", at=1)
    add_request(g, session_id="s1", request_id="p1", text="add avatar", at=10)
    add_edit(g, request_id="p1", edit_id="e1", tool="Edit", path="Card.tsx", summary="", at=11)
    add_request(g, session_id="be", request_id="p2", text="rename avatar field", at=20)
    add_edit(g, request_id="p2", edit_id="e2", tool="Edit", path="Card.tsx", summary="", at=21)
    add_edit(g, request_id="p2", edit_id="e3", tool="Edit", path="api.py", summary="", at=22)


def test_recent_edit_by_another_session_is_found(ready: Graph) -> None:
    _setup(ready)
    found = recent_edits_by_others(ready, path="Card.tsx", session_id="s1", since=15)
    assert [(o.role, o.request_text, o.at) for o in found] == [
        ("backend", "rename avatar field", 21)
    ]


def test_own_and_old_edits_are_ignored(ready: Graph) -> None:
    _setup(ready)
    assert recent_edits_by_others(ready, path="Card.tsx", session_id="be", since=15) == []
    assert recent_edits_by_others(ready, path="Card.tsx", session_id="s1", since=25) == []


def test_files_changed_by_more_than_one_role_are_listed(ready: Graph) -> None:
    _setup(ready)
    assert [(f.path, f.roles) for f in shared_files(ready, since=0)] == [
        ("Card.tsx", ("backend", "frontend"))
    ]


def test_latest_of_several_edits_by_a_session_is_reported(ready: Graph) -> None:
    _setup(ready)
    add_request(ready, session_id="be", request_id="p3", text="newest change", at=30)
    add_edit(ready, request_id="p3", edit_id="e4", tool="Edit", path="Card.tsx", summary="", at=31)
    found = recent_edits_by_others(ready, path="Card.tsx", session_id="s1", since=15)
    assert [(o.request_text, o.at) for o in found] == [("newest change", 31)]


def test_own_process_is_not_reported_after_clear(ready: Graph) -> None:
    # /clear: same Claude process (pid 7) gets a new session id.
    upsert_session(ready, session_id="old", role="frontend", cwd="/w", at=1, pid=7)
    add_request(ready, session_id="old", request_id="p1", text="before clear", at=10)
    add_edit(ready, request_id="p1", edit_id="e1", tool="Edit", path="Card.tsx", summary="", at=11)
    upsert_session(ready, session_id="new", role="frontend", cwd="/w", at=20, pid=7)
    found = recent_edits_by_others(ready, path="Card.tsx", session_id="new", since=0, pid=7)
    assert found == []
