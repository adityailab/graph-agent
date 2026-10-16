from __future__ import annotations

import re

from falkordb import Graph

from handoff.config import Config
from handoff.graph.connection import connect
from handoff.graph.history import handoff_requests
from handoff.graph.requests import add_request
from handoff.graph.schema import ensure_schema
from handoff.graph.sessions import upsert_session
from handoff.mcp.context import UNREACHABLE, ToolContext
from handoff.mcp.read_tools import handoff
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


def test_need_can_be_resolved_using_the_id_shown_in_the_handoff(backend: ToolContext) -> None:
    frontend = ToolContext(graph=backend.graph, role="frontend", cwd="/w", now=lambda: 2_000)
    record_need(frontend, "backend", "return avatarUrl")
    shown = handoff(backend, role="frontend")
    need_id = re.search(r"\(open, id (\w+)\)", shown)
    assert need_id is not None
    assert resolve_need(backend, need_id.group(1)).startswith("Need")


def test_confirmation_names_the_request_it_attached_to(frontend: ToolContext) -> None:
    reply = record_decision(frontend, "read avatarUrl", "server owns urls", "profile")
    assert '"show avatar"' in reply


def test_two_sessions_sharing_a_role_are_warned(frontend: ToolContext) -> None:
    upsert_session(frontend.graph, session_id="fe2", role="frontend", cwd="/w", at=1_900)
    add_request(frontend.graph, session_id="fe2", request_id="p2", text="other work", at=1_900)
    reply = record_decision(frontend, "x", "y", "z")
    assert "2 sessions share the role frontend" in reply


def test_roles_are_matched_without_case_or_spaces(backend: ToolContext) -> None:
    frontend = ToolContext(graph=backend.graph, role="frontend", cwd="/w", now=lambda: 2_000)
    record_need(frontend, " Backend ", "return avatarUrl")
    assert "Needs from backend" in handoff(backend, role=" Frontend ")


def test_unreachable_graph_gives_a_sentence_not_an_error(config: Config) -> None:
    dead = ToolContext.lazy(
        connect=lambda: connect(Config(host="localhost", port=1, graph_name="x", home=config.home)),
        role="frontend",
        cwd="/w",
    )
    assert record_decision(dead, "x", "y", "z") == UNREACHABLE
    assert handoff(dead) == UNREACHABLE


def test_session_id_from_claude_code_picks_the_exact_session(frontend: ToolContext) -> None:
    # A second frontend terminal was seen more recently, but this server knows its own id.
    upsert_session(frontend.graph, session_id="fe2", role="frontend", cwd="/w", at=1_900)
    add_request(frontend.graph, session_id="fe2", request_id="p2", text="other work", at=1_900)
    mine = ToolContext(
        graph=frontend.graph, role="frontend", cwd="/w", now=lambda: 2_000, session_id="fe"
    )
    reply = record_decision(mine, "x", "y", "z")
    assert '"show avatar"' in reply
    assert "share the role" not in reply
