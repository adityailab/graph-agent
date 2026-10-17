from __future__ import annotations

from falkordb import Graph

from handoff.graph.decisions import add_decision
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


def test_decisions_of_one_request_come_in_the_order_they_were_made(two_sessions: Graph) -> None:
    # ids sort the other way round from the times: the id must not decide the order
    for decision_id, text, at in (("zz", "first thing decided", 500), ("aa", "second", 600)):
        add_decision(
            two_sessions,
            request_id="p3",
            decision_id=decision_id,
            text=text,
            reason="r",
            topic="order",
            at=at,
        )
    [view] = [v for v in handoff_requests(two_sessions, role="backend", since=0) if v.id == "p3"]
    assert [d.text for d in view.decisions] == ["first thing decided", "second"]
    assert [d.at for d in view.decisions] == [500, 600]
