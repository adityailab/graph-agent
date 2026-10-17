from __future__ import annotations

import pytest

from handoff.mcp.context import ToolContext
from handoff.mcp.server import build_server

EXPECTED_TOOLS = {
    "record_decision",
    "record_need",
    "resolve_need",
    "sessions",
    "handoff",
    "why",
    "graph_guide",
    "send_message",
    "ask",
    "search",
    "connection",
    "ask_graph",
    "concepts",
    "supersede_decision",
    "timeline",
    "record_convention",
    "conventions",
    "retire_convention",
}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_server_offers_every_tool_with_a_description(frontend: ToolContext) -> None:
    tools = await build_server(frontend).list_tools()
    assert {t.name for t in tools} == EXPECTED_TOOLS
    assert all(t.description for t in tools)


@pytest.mark.anyio
async def test_calling_a_tool_through_the_server_reaches_the_graph(frontend: ToolContext) -> None:
    server = build_server(frontend)
    await server.call_tool(
        "record_decision", {"text": "read avatarUrl", "reason": "server owns urls", "topic": "p"}
    )
    result = await server.call_tool("handoff", {"role": "frontend"})
    assert "read avatarUrl" in str(result)
