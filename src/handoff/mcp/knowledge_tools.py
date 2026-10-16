"""Knowledge tools: questions and concepts answered from the GraphRAG knowledge graph."""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from handoff.knowledge.answers import answer_question, find_concepts
from handoff.mcp.context import ToolContext, guarded
from handoff.models.base import ModelUnavailable

NOT_RUNNING = (
    "The knowledge layer is not running. It needs the optional extra "
    "(uv sync --extra knowledge) and HANDOFF_KNOWLEDGE not set to off."
)


@guarded
def ask_graph(ctx: ToolContext, question: str) -> str:
    """Answer from the knowledge graph built from every session's requests and decisions."""
    if ctx.knowledge is None:
        return NOT_RUNNING
    if not question.strip():
        return "Not asked: question is empty."
    try:
        return answer_question(ctx.knowledge.rag, ctx.knowledge.kg, ctx.graph, question)
    except ModelUnavailable as exc:
        return f"No answer from the knowledge graph: {exc}."


@guarded
def concepts(ctx: ToolContext, query: str) -> str:
    """Concepts the sessions' work mentions, and which work mentions each."""
    if ctx.knowledge is None:
        return NOT_RUNNING
    if not query.strip():
        return "Not searched: query is empty."
    return find_concepts(ctx.knowledge.kg, ctx.graph, query)


def register(server: MCPServer, ctx: ToolContext) -> None:
    """Add the knowledge tools to the server."""

    @server.tool(
        name="ask_graph",
        description="Ask a question answered from the knowledge graph of all sessions' work.",
    )
    def _ask_graph(
        question: Annotated[str, Field(description="The question, in plain words.")],
    ) -> str:
        return ask_graph(ctx, question)

    @server.tool(
        name="concepts",
        description="Find concepts (fields, endpoints, components) and the work naming them.",
    )
    def _concepts(
        query: Annotated[str, Field(description="A concept or words to look for.")],
    ) -> str:
        return concepts(ctx, query)
