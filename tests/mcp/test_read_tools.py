from __future__ import annotations

from handoff.graph.edits import add_edit
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
    assert "Needs from backend: return avatarUrl (open)" in text


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
