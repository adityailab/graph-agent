from __future__ import annotations

import pytest
from falkordb import Graph

from handoff.graph.requests import add_request
from handoff.graph.schema import ensure_schema
from handoff.graph.sessions import upsert_session
from handoff.mcp.context import ToolContext


@pytest.fixture
def frontend(graph: Graph) -> ToolContext:
    """Tool context for a frontend session at /w that is working on request p1."""
    ensure_schema(graph)
    upsert_session(graph, session_id="fe", role="frontend", cwd="/w", at=1_000)
    add_request(graph, session_id="fe", request_id="p1", text="show avatar", at=1_000)
    return ToolContext(graph=graph, role="frontend", cwd="/w", now=lambda: 2_000)


@pytest.fixture
def backend(frontend: ToolContext) -> ToolContext:
    """Tool context for a backend session at /w, working on request p9."""
    upsert_session(frontend.graph, session_id="be", role="backend", cwd="/w", at=1_500)
    add_request(frontend.graph, session_id="be", request_id="p9", text="pick up", at=1_500)
    return ToolContext(graph=frontend.graph, role="backend", cwd="/w", now=lambda: 2_000)
