from __future__ import annotations

from falkordb import Graph

from handoff.graph.decisions import add_decision
from handoff.graph.history import handoff_requests
from handoff.graph.requests import add_request
from handoff.graph.timeline import current_on_topic, supersede_decision, topic_timeline


def _replace_on_profile(graph: Graph) -> None:
    add_decision(
        graph,
        request_id="p3",
        decision_id="d2",
        text="urls come from the CDN",
        reason="the server stopped owning them",
        topic="Profile",
        at=300,
    )


def test_a_topic_timeline_lists_decisions_oldest_first_with_who_and_when(
    two_sessions: Graph,
) -> None:
    _replace_on_profile(two_sessions)
    timeline = topic_timeline(two_sessions, "profile")
    assert [(e.decision_id, e.role, e.at) for e in timeline] == [
        ("d1", "frontend", 112),
        ("d2", "backend", 300),
    ]
    assert all(e.replaced_by is None for e in timeline)


def test_superseding_marks_the_old_decision_as_replaced(two_sessions: Graph) -> None:
    _replace_on_profile(two_sessions)
    assert supersede_decision(two_sessions, new_id="d2", old_id="d1", at=301)
    old = topic_timeline(two_sessions, "profile")[0]
    assert old.replaced_by == "d2"


def test_only_decisions_still_in_force_are_current(two_sessions: Graph) -> None:
    _replace_on_profile(two_sessions)
    supersede_decision(two_sessions, new_id="d2", old_id="d1", at=301)
    current = current_on_topic(two_sessions, "profile", excluding="")
    assert [e.decision_id for e in current] == ["d2"]
    assert current_on_topic(two_sessions, "profile", excluding="d2") == []


def test_superseding_a_decision_that_does_not_exist_is_refused(two_sessions: Graph) -> None:
    assert not supersede_decision(two_sessions, new_id="d1", old_id="nope", at=5)


def test_a_replaced_decision_is_flagged_in_the_handoff(two_sessions: Graph) -> None:
    _replace_on_profile(two_sessions)
    supersede_decision(two_sessions, new_id="d2", old_id="d1", at=301)
    add_request(two_sessions, session_id="fe", request_id="p9", text="later", at=400)
    flags = {
        d.id: d.superseded
        for r in handoff_requests(two_sessions, role=None, since=0)
        for d in r.decisions
    }
    assert flags == {"d1": True, "d2": False}
