from __future__ import annotations

import re

from falkordb import Graph

from handoff.graph.history import handoff_requests
from handoff.graph.schema import ensure_schema
from handoff.mcp.context import ToolContext
from handoff.mcp.record_tools import record_decision, record_need, resolve_need


def test_decision_is_recorded_on_the_current_request(frontend: ToolContext) -> None:
    reply = record_decision(frontend, "read avatarUrl", "server owns urls", "profile")
    assert reply.startswith("Recorded decision")
    (request,) = handoff_requests(frontend.graph, role="frontend", since=0)
    assert [d.text for d in request.decisions] == ["read avatarUrl"]


def test_blank_fields_are_refused_by_name(frontend: ToolContext) -> None:
    assert record_decision(frontend, "x", "y", "   ") == "Not recorded: topic is empty."
    assert record_need(frontend, "", "x") == "Not recorded: for_role is empty."


def test_session_without_a_request_is_told_so(graph: Graph) -> None:
    ensure_schema(graph)  # the server does this at start, so the graph always exists
    ctx = ToolContext(graph=graph, role="deploy", cwd="/w", now=lambda: 1)
    reply = record_decision(ctx, "x", "y", "z")
    assert reply.startswith("Not recorded: no request")


def test_need_is_raised_then_resolved_by_another_role(backend: ToolContext) -> None:
    frontend = ToolContext(graph=backend.graph, role="frontend", cwd="/w", now=lambda: 2_000)
    reply = record_need(frontend, "backend", "return avatarUrl")
    need_id = re.search(r"need (\w+)", reply)
    assert need_id is not None
    assert resolve_need(backend, need_id.group(1)).startswith("Need")
    (request,) = handoff_requests(backend.graph, role="frontend", since=0)
    assert request.needs[0].status == "resolved"


def test_resolving_an_unknown_need_is_told_so(frontend: ToolContext) -> None:
    assert resolve_need(frontend, "nope") == "No need with id nope."
