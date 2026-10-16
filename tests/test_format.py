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
    assert "Needs from backend: return avatarUrl (open)" in text


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
