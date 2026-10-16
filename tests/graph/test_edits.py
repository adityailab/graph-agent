from __future__ import annotations

from falkordb import Graph

from handoff.graph.edits import add_edit
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
