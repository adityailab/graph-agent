from __future__ import annotations

import pytest
from falkordb import Graph

from handoff.graph.messages import add_message, claim_pending_messages
from handoff.graph.schema import ensure_schema
from handoff.graph.sessions import upsert_session


@pytest.fixture
def three(graph: Graph) -> Graph:
    """A backend session and two frontend terminals."""
    ensure_schema(graph)
    upsert_session(graph, session_id="be", role="backend", cwd="/w", at=1)
    upsert_session(graph, session_id="fe1", role="frontend", cwd="/w", at=1)
    upsert_session(graph, session_id="fe2", role="frontend", cwd="/w", at=1)
    return graph


def _send(graph: Graph, mid: str, *, reply_to: str | None = None, at: int = 10) -> None:
    assert add_message(
        graph,
        message_id=mid,
        from_session_id="be",
        to_role="frontend",
        kind="message",
        text=f"text {mid}",
        reply_to=reply_to,
        at=at,
    )


def test_message_is_delivered_once(three: Graph) -> None:
    _send(three, "m1")
    first = claim_pending_messages(three, session_id="fe1", role="frontend", since=0, at=20)
    assert [(m.id, m.from_role, m.text) for m in first] == [("m1", "backend", "text m1")]
    assert claim_pending_messages(three, session_id="fe1", role="frontend", since=0, at=21) == []


def test_role_message_reaches_each_session_once(three: Graph) -> None:
    _send(three, "m1")
    for sid in ("fe1", "fe2"):
        assert (
            len(claim_pending_messages(three, session_id=sid, role="frontend", since=0, at=20)) == 1
        )
        assert claim_pending_messages(three, session_id=sid, role="frontend", since=0, at=21) == []


def test_sender_does_not_receive_its_own_message(three: Graph) -> None:
    add_message(
        three,
        message_id="m1",
        from_session_id="fe1",
        to_role="frontend",
        kind="message",
        text="note to self",
        reply_to=None,
        at=10,
    )
    assert claim_pending_messages(three, session_id="fe1", role="frontend", since=0, at=20) == []
    assert (
        len(claim_pending_messages(three, session_id="fe2", role="frontend", since=0, at=20)) == 1
    )


def test_messages_come_oldest_first_and_old_ones_are_skipped(three: Graph) -> None:
    _send(three, "old", at=5)
    _send(three, "m2", at=12)
    _send(three, "m1", at=11)
    got = claim_pending_messages(three, session_id="fe1", role="frontend", since=10, at=20)
    assert [m.id for m in got] == ["m1", "m2"]


def test_reply_keeps_its_thread(three: Graph) -> None:
    _send(three, "q1")
    _send(three, "a1", reply_to="q1", at=11)
    got = claim_pending_messages(three, session_id="fe1", role="frontend", since=0, at=20)
    assert [(m.id, m.reply_to) for m in got] == [("q1", None), ("a1", "q1")]


def test_message_from_unknown_session_is_refused(three: Graph) -> None:
    assert not add_message(
        three,
        message_id="m1",
        from_session_id="nope",
        to_role="frontend",
        kind="message",
        text="x",
        reply_to=None,
        at=1,
    )


def test_resent_message_is_not_duplicated(three: Graph) -> None:
    _send(three, "m1")
    _send(three, "m1")
    assert (
        len(claim_pending_messages(three, session_id="fe1", role="frontend", since=0, at=20)) == 1
    )
