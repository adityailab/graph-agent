from __future__ import annotations

from handoff.graph.edits import add_edit
from handoff.mcp.connection_tool import connection
from handoff.mcp.context import ToolContext


def test_connection_is_rendered_as_a_chain(backend: ToolContext) -> None:
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
    text = connection(backend, " Frontend ")
    assert text.splitlines()[0] == "How this session's work connects to the frontend session's:"
    assert (
        'this request "pick up" → changed file Card.tsx → changed by frontend request "show avatar"'
        in text
    )


def test_no_connection_says_so(backend: ToolContext) -> None:
    assert connection(backend, "frontend").startswith("No chain of work links")


def test_blank_role_is_refused(backend: ToolContext) -> None:
    assert connection(backend, " ") == "Not traced: role is empty."
