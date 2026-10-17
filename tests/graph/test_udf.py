from __future__ import annotations

import pytest
from falkordb import Graph

from handoff.graph.edits import add_edit
from handoff.graph.requests import add_request
from handoff.graph.udf import UDF_LIBRARY, file_overlap, load_udfs


@pytest.fixture
def two_requests(ready: Graph) -> Graph:
    """p1 changed a.ts and b.ts; p2 changed b.ts and c.ts."""
    add_request(ready, session_id="s1", request_id="p1", text="first", at=1)
    add_request(ready, session_id="s1", request_id="p2", text="second", at=2)
    for rid, eid, path in (
        ("p1", "e1", "a.ts"),
        ("p1", "e2", "b.ts"),
        ("p2", "e3", "b.ts"),
        ("p2", "e4", "c.ts"),
    ):
        add_edit(ready, request_id=rid, edit_id=eid, tool="Edit", path=path, summary="", at=3)
    return ready


def test_overlap_is_the_share_of_files_two_requests_both_changed(two_requests: Graph) -> None:
    assert load_udfs(two_requests) is True
    assert file_overlap(two_requests, "p1", "p2") == pytest.approx(1 / 3)


def test_loading_again_is_harmless(two_requests: Graph) -> None:
    assert load_udfs(two_requests) is True
    assert load_udfs(two_requests) is True
    assert file_overlap(two_requests, "p1", "p1") == pytest.approx(1.0)


def test_without_the_library_overlap_is_unknown_not_an_error(two_requests: Graph) -> None:
    two_requests.execute_command("GRAPH.UDF", "DELETE", UDF_LIBRARY)
    try:
        assert file_overlap(two_requests, "p1", "p2") is None
    finally:
        load_udfs(two_requests)
