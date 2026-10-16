from __future__ import annotations

from handoff.format import render_handoff, select_requests
from handoff.graph.records import DecisionView, NeedView, RequestView


def _request(i: int, *, need: bool = False) -> RequestView:
    needs = (NeedView(id=f"n{i}", text="return avatarUrl", for_role="backend", status="open"),)
    return RequestView(
        id=f"p{i}",
        role="frontend",
        seq=i,
        text=f"request {i}",
        at=i,
        files=("Card.tsx",),
        decisions=(DecisionView(id=f"d{i}", text="read avatarUrl", reason="server owns urls"),),
        needs=needs if need else (),
    )


def test_render_shows_prompt_decision_files_and_need() -> None:
    text = render_handoff([_request(1, need=True)])
    assert "frontend session: 1 request, 1 file changed" in text
    assert 'Request 1 (person): "request 1"' in text
    assert "Decided: read avatarUrl" in text
    assert "Why: server owns urls" in text
    assert "Changed: Card.tsx" in text
    assert "Needs from backend: return avatarUrl (open, id n1)" in text


def test_render_of_nothing_says_so() -> None:
    assert render_handoff([]) == "No requests recorded in this period."


def test_selection_keeps_everything_under_the_limit() -> None:
    requests = [_request(i) for i in range(1, 4)]
    assert select_requests(requests, limit=5) == requests


def test_selection_respects_the_limit_and_keeps_order() -> None:
    requests = [_request(i) for i in range(1, 21)]
    chosen = select_requests(requests, limit=5)
    assert len(chosen) == 5
    assert [r.seq for r in chosen] == sorted(r.seq for r in chosen)


def test_selection_never_drops_a_request_with_an_open_need() -> None:
    requests = [_request(1, need=True)] + [_request(i) for i in range(2, 21)]
    assert requests[0] in select_requests(requests, limit=5)


def test_messages_render_as_facts_with_reply_ids() -> None:
    from handoff.format import render_messages
    from handoff.graph.records import MessageView

    text = render_messages(
        [
            MessageView(
                id="m1", kind="message", from_role="backend", text="done", reply_to=None, at=0
            ),
            MessageView(
                id="q1", kind="question", from_role="deploy", text="env?", reply_to=None, at=0
            ),
        ]
    )
    assert "from the backend session" in text
    assert "Question q1 from the deploy session" in text
    assert "reply_to set to q1" in text


def test_many_messages_are_capped() -> None:
    from handoff.format import MAX_MESSAGES, render_messages
    from handoff.graph.records import MessageView

    many = [
        MessageView(
            id=f"m{i}", kind="message", from_role="b", text="x" * 2_000, reply_to=None, at=0
        )
        for i in range(MAX_MESSAGES + 5)
    ]
    text = render_messages(many)
    assert "5 more messages" in text
    assert len(text) < (MAX_MESSAGES + 1) * 700


def test_search_lines_do_not_double_their_full_stops() -> None:
    from handoff.format_search import render_search
    from handoff.graph.records import DecisionHit

    hit = DecisionHit(
        id="d1",
        role="frontend",
        request_text="r",
        text="Keep JWT.",
        reason="Safer.",
        files=(),
        related_roles=(),
    )
    assert ".." not in render_search("q", [hit])
