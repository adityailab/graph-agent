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
