from __future__ import annotations

from falkordb import Graph

from handoff.graph.consultations import add_consultations
from handoff.graph.messages import add_message
from handoff.graph.overview import handoffs, message_flows, role_stats


def _talk(g: Graph) -> Graph:
    add_message(
        g,
        message_id="m1",
        from_session_id="be",
        to_role="frontend",
        kind="message",
        text="avatarUrl is live",
        reply_to=None,
        at=220,
    )
    add_consultations(g, request_id="p3", consulted_ids=["p1"], at=230)
    return g


def test_each_role_has_its_counts(two_sessions: Graph) -> None:
    stats = {s.role: s for s in role_stats(_talk(two_sessions), since=0)}
    fe, be = stats["frontend"], stats["backend"]
    assert (fe.requests, fe.decisions, fe.edits) == (2, 1, 2)
    assert (be.requests, be.messages_sent, be.open_needs) == (1, 1, 1)


def test_flows_say_who_talked_to_whom_and_how(two_sessions: Graph) -> None:
    flows = {(f.source, f.target, f.kind): f.count for f in message_flows(_talk(two_sessions))}
    assert flows[("backend", "frontend", "message")] == 1
    assert flows[("frontend", "backend", "read")] == 1  # work flows from author to reader
    assert flows[("frontend", "backend", "need")] == 1


def test_a_handoff_carries_the_decision_and_its_reason(two_sessions: Graph) -> None:
    (found,) = handoffs(_talk(two_sessions), limit=10)
    assert (found.reader, found.author, found.request) == ("backend", "frontend", "show avatar")
    assert found.decisions == (("read avatarUrl", "server owns urls"),)


def test_a_read_of_work_without_decisions_has_none(two_sessions: Graph) -> None:
    add_consultations(two_sessions, request_id="p3", consulted_ids=["p2"], at=240)
    latest = handoffs(two_sessions, limit=10)[0]
    assert latest.request == "tidy styles"
    assert latest.decisions == ()
