from __future__ import annotations

from falkordb import Graph

from handoff.graph.communication import communication_counts
from handoff.graph.consultations import add_consultations


def test_counts_what_the_sessions_did_for_each_other(two_sessions: Graph) -> None:
    add_consultations(two_sessions, request_id="p3", consulted_ids=["p1"], at=300)
    counts = communication_counts(two_sessions)
    assert counts == {"delivered_messages": 0, "cited_answers": 0, "consultations": 1}
