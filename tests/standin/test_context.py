from __future__ import annotations

from falkordb import Graph

from handoff.standin.context import context_ids, gather_context


def test_context_holds_only_that_roles_history(history: Graph) -> None:
    ctx = gather_context(history, role="frontend", since=0, limit=10)
    assert [r.id for r in ctx.requests] == ["p1"]
    assert [d.id for d in ctx.requests[0].decisions] == ["d1"]
    assert [m.id for m in ctx.messages] == ["m1"]


def test_context_ids_cover_requests_decisions_needs_and_messages(history: Graph) -> None:
    ctx = gather_context(history, role="frontend", since=0, limit=10)
    assert context_ids(ctx) == {"p1", "d1", "n1", "m1"}


def test_context_respects_the_limit(history: Graph) -> None:
    for i in range(5):
        from handoff.graph.requests import add_request

        add_request(history, session_id="fe", request_id=f"x{i}", text=f"r{i}", at=200 + i)
    assert len(gather_context(history, role="frontend", since=0, limit=3).requests) == 3


def test_reading_context_delivers_nothing(history: Graph) -> None:
    from handoff.graph.messages import claim_pending_messages

    gather_context(history, role="frontend", since=0, limit=10)
    assert (
        len(claim_pending_messages(history, session_id="fe", role="frontend", since=0, at=999)) == 1
    )


def test_questions_and_stand_in_answers_are_not_history(history: Graph) -> None:
    from handoff.graph.messages import add_message

    add_message(
        history,
        message_id="q1",
        from_session_id="be",
        to_role="frontend",
        kind="question",
        text="we agreed null is fine, right?",
        reply_to=None,
        at=140,
    )
    add_message(
        history,
        message_id="a1",
        from_session_id="be",
        to_role="frontend",
        kind="standin_answer",
        text="yes",
        reply_to="q1",
        at=141,
    )
    ctx = gather_context(history, role="frontend", since=0, limit=10)
    assert [m.id for m in ctx.messages] == ["m1"]
    assert {"q1", "a1"}.isdisjoint(context_ids(ctx))
