from __future__ import annotations

from falkordb import Graph

from handoff.graph.decisions import add_decision
from handoff.graph.edits import add_edit, why_file
from handoff.graph.records import DecisionView
from handoff.graph.requests import add_request


def test_edit_links_request_to_file(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    assert add_edit(
        ready, request_id="p1", edit_id="t1", tool="Edit", path="src/a.ts", summary="-a\n+b", at=2
    )
    rows = ready.query(
        "MATCH (:Request {id: 'p1'})-[:CAUSED]->(e:Edit)-[:TOUCHED]->(f:File) "
        "RETURN e.tool, e.summary, f.path"
    ).result_set
    assert rows == [["Edit", "-a\n+b", "src/a.ts"]]


def test_replayed_edit_is_not_duplicated(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    for _ in range(2):
        add_edit(ready, request_id="p1", edit_id="t1", tool="Edit", path="a", summary="", at=2)
    assert ready.query("MATCH (e:Edit) RETURN count(e)").result_set == [[1]]
    assert ready.query("MATCH ()-[c:CAUSED]->() RETURN count(c)").result_set == [[1]]


def test_edit_for_unknown_request_is_refused(ready: Graph) -> None:
    assert not add_edit(
        ready, request_id="nope", edit_id="t1", tool="Edit", path="a", summary="", at=2
    )


def test_why_file_lists_newest_edit_first_with_decisions(two_sessions: Graph) -> None:
    rows = why_file(two_sessions, "Card.tsx")
    assert [r.request_text for r in rows] == ["tidy styles", "show avatar"]
    assert rows[0].decisions == ()
    assert rows[1].decisions == (
        DecisionView(id="d1", text="read avatarUrl", reason="server owns urls"),
    )


def test_why_file_gives_one_row_per_edit_however_many_decisions(ready: Graph) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="one", at=1)
    add_edit(ready, request_id="p1", edit_id="e1", tool="Edit", path="a.ts", summary="", at=2)
    for i in range(3):
        add_decision(
            ready, request_id="p1", decision_id=f"d{i}", text=f"t{i}", reason="r", topic="x", at=3
        )
    rows = why_file(ready, "a.ts")
    assert len(rows) == 1
    assert sorted(d.id for d in rows[0].decisions) == ["d0", "d1", "d2"]
