from __future__ import annotations

from falkordb import Graph

from handoff.graph.consultations import add_consultations
from handoff.graph.feed import recent_events
from handoff.graph.messages import add_message


def test_events_of_every_kind_come_in_time_order(two_sessions: Graph) -> None:
    add_message(
        two_sessions,
        message_id="m1",
        from_session_id="be",
        to_role="frontend",
        kind="message",
        text="avatarUrl is live",
        reply_to=None,
        at=220,
    )
    add_consultations(two_sessions, request_id="p3", consulted_ids=["p1"], at=230)
    events = recent_events(two_sessions, limit=50)
    kinds = [e.kind for e in events]
    for kind in ("asked", "DECIDED", "NEEDS", "edited", "MESSAGE", "READ"):
        assert kind in kinds
    assert [e.at for e in events] == sorted(e.at for e in events)
    read = next(e for e in events if e.kind == "READ")
    assert (read.role, "frontend") == ("backend", read.text.split()[0])


def test_only_the_newest_events_are_kept(two_sessions: Graph) -> None:
    events = recent_events(two_sessions, limit=2)
    assert len(events) == 2
    assert events[-1].text == "pick up frontend"


def test_events_older_than_the_window_are_left_out(two_sessions: Graph) -> None:
    everything = recent_events(two_sessions, limit=50)
    recent = recent_events(two_sessions, limit=50, since=200)
    assert len(recent) < len(everything)
    assert all(e.at >= 200 for e in recent)
