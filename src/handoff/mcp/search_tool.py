"""The search tool: FalkorDB full-text and vector search, merged, then read through the graph."""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from handoff.format_search import render_search
from handoff.graph.search import decision_hits, fulltext_decisions, similar_decisions
from handoff.mcp.context import ToolContext, guarded

MAX_DISTANCE = 0.35  # cosine distance; related texts measured about 0.18, unrelated 0.56
_RRF_K = 60


def fuse(ranked_lists: list[list[str]], *, k: int) -> list[str]:
    """Reciprocal rank fusion: items ranked well in several lists come first."""
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked):
            scores[item] = scores.get(item, 0.0) + 1.0 / (_RRF_K + rank + 1)
    return sorted(scores, key=lambda item: -scores[item])[:k]


def rank_decisions(ctx: ToolContext, query: str, *, k: int) -> list[str]:
    """Decision ids matching `query` by words and (when an embedder is set) meaning."""
    lists = [[d for d, _ in fulltext_decisions(ctx.graph, query, k=2 * k)]]
    if ctx.embedder is not None:
        vector = ctx.embedder.embed([query])[0]
        near = similar_decisions(ctx.graph, vector, k=2 * k)
        lists.append([d for d, distance in near if distance <= MAX_DISTANCE])
    return fuse(lists, k=k)


@guarded
def search(ctx: ToolContext, query: str, k: int = 5) -> str:
    """Find recorded decisions by words and by meaning, with who made them and why."""
    if not query.strip():
        return "Not searched: query is empty."
    k = max(1, min(k, 20))
    hits = decision_hits(ctx.graph, rank_decisions(ctx, query, k=k))
    return render_search(query, hits) if hits else "No recorded decisions match."


def register(server: MCPServer, ctx: ToolContext) -> None:
    """Add the search tool to the server."""

    @server.tool(
        name="search",
        description="Find recorded decisions by words and meaning, with who made them and why.",
    )
    def _search(
        query: Annotated[str, Field(description="What to look for, in plain words.")],
        k: Annotated[int, Field(description="Most results to show, 1 to 20.")] = 5,
    ) -> str:
        return search(ctx, query, k)
