from __future__ import annotations

from falkordb import Graph

from handoff.graph.history import handoff_requests
from handoff.graph.records import DecisionView, NeedView


def test_handoff_bundles_files_decisions_and_needs(two_sessions: Graph) -> None:
    requests = handoff_requests(two_sessions, role="frontend", since=0)
    assert [r.id for r in requests] == ["p1", "p2"]
    first = requests[0]
    assert first.files == ("Card.tsx",)
    assert first.decisions == (
        DecisionView(id="d1", text="read avatarUrl", reason="server owns urls"),
    )
    assert first.needs == (
        NeedView(id="n1", text="return avatarUrl", for_role="backend", status="open"),
    )


def test_handoff_request_without_decisions_has_empty_tuples(two_sessions: Graph) -> None:
    second = handoff_requests(two_sessions, role="frontend", since=0)[1]
    assert (second.decisions, second.needs) == ((), ())


def test_handoff_filters_by_time_and_covers_all_roles(two_sessions: Graph) -> None:
    assert [r.id for r in handoff_requests(two_sessions, role="frontend", since=115)] == ["p2"]
    assert [r.id for r in handoff_requests(two_sessions, role=None, since=0)] == [
        "p1",
        "p2",
        "p3",
    ]
