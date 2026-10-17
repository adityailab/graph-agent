from __future__ import annotations

import pytest

from handoff.graph.edits import add_edit
from handoff.graph.requests import add_request
from handoff.mcp.context import ToolContext
from handoff.mcp.read_tools import handoff, sessions, why
from handoff.mcp.record_tools import record_decision, record_need


def test_sessions_lists_roles_and_what_each_is_working_on(backend: ToolContext) -> None:
    text = sessions(backend)
    assert "frontend" in text
    assert "show avatar" in text
    assert "backend (this session)" in text


def test_handoff_shows_another_roles_intent(backend: ToolContext) -> None:
    frontend = ToolContext(graph=backend.graph, role="frontend", cwd="/w", now=lambda: 2_000)
    record_decision(frontend, "read avatarUrl", "server owns urls", "profile")
    record_need(frontend, "backend", "return avatarUrl")
    text = handoff(backend, role="frontend")
    assert '"show avatar"' in text
    assert "Why: server owns urls" in text
    assert "Needs from backend: return avatarUrl (open, id " in text


def test_handoff_respects_the_time_window(backend: ToolContext) -> None:
    assert handoff(backend, role="frontend", since_minutes=0) == (
        "No requests recorded in this period."
    )


def test_why_accepts_absolute_or_relative_paths(frontend: ToolContext) -> None:
    add_edit(
        frontend.graph,
        request_id="p1",
        edit_id="e1",
        tool="Edit",
        path="Card.tsx",
        summary="+img",
        at=1_100,
    )
    record_decision(frontend, "read avatarUrl", "server owns urls", "profile")
    for path in ("Card.tsx", "/w/Card.tsx"):
        text = why(frontend, path)
        assert "show avatar" in text
        assert "read avatarUrl" in text


def test_why_for_an_unknown_file_says_so(frontend: ToolContext) -> None:
    assert why(frontend, "nothing.ts") == "No recorded edits to nothing.ts."


def test_why_normalises_dot_segments(frontend: ToolContext) -> None:
    add_edit(
        frontend.graph,
        request_id="p1",
        edit_id="e1",
        tool="Edit",
        path="src/a.ts",
        summary="+x",
        at=1_100,
    )
    assert "show avatar" in why(frontend, "./src/../src/a.ts")


def test_long_request_text_is_shortened_in_listings(frontend: ToolContext) -> None:
    add_request(frontend.graph, session_id="fe", request_id="p2", text="y" * 5_000, at=1_200)
    assert len(sessions(frontend)) < 600


def test_out_of_range_window_and_limit_are_clamped(frontend: ToolContext) -> None:
    assert "show avatar" in handoff(frontend, role="frontend", since_minutes=10**12, limit=0)
    assert "-5" not in sessions(frontend, within_minutes=-5)


def test_handoff_lists_files_changed_by_more_than_one_role(backend: ToolContext) -> None:
    add_edit(
        backend.graph,
        request_id="p1",
        edit_id="e1",
        tool="Edit",
        path="Card.tsx",
        summary="",
        at=1_100,
    )
    add_edit(
        backend.graph,
        request_id="p9",
        edit_id="e9",
        tool="Edit",
        path="Card.tsx",
        summary="",
        at=1_600,
    )
    assert "Changed by more than one role: Card.tsx (backend, frontend)" in handoff(backend)


def test_reading_a_handoff_records_what_was_consulted(backend: ToolContext) -> None:
    handoff(backend, role="frontend")
    rows = backend.graph.query(
        "MATCH (:Request {id: 'p9'})-[:CONSULTED]->(c:Request) RETURN c.id"
    ).result_set
    assert rows == [["p1"]]


def test_handoff_ends_with_what_matters_now(backend: ToolContext) -> None:
    for rid, eid in (("p1", "e1"), ("p9", "e9")):
        add_edit(
            backend.graph,
            request_id=rid,
            edit_id=eid,
            tool="Edit",
            path="Card.tsx",
            summary="x",
            at=1_600,
        )
    text = handoff(backend)
    assert "What matters now:" in text
    assert "backend and frontend both changed Card.tsx" in text


def test_a_failing_insight_refresh_does_not_break_the_handoff(
    backend: ToolContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    from redis.exceptions import ResponseError

    def broken(*args: object, **kwargs: object) -> None:
        raise ResponseError("unknown relationship-type RELATES")

    monkeypatch.setattr("handoff.mcp.insights_view.refresh_insights", broken)
    text = handoff(backend, role="frontend")
    assert '"show avatar"' in text
    assert "unreachable" not in text


def test_recording_who_read_never_costs_the_reply(
    backend: ToolContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    from redis.exceptions import ResponseError

    def broken(*args: object, **kwargs: object) -> None:
        raise ResponseError("write refused")

    monkeypatch.setattr("handoff.mcp.read_tools.add_consultations", broken)
    text = handoff(backend, role="frontend")
    assert '"show avatar"' in text
    assert "unreachable" not in text


def test_the_lean_lookup_finds_the_same_request(backend: ToolContext) -> None:
    from handoff.mcp.current import current_request, current_request_id

    full = current_request(backend)
    assert full is not None
    assert current_request_id(backend) == full.id
