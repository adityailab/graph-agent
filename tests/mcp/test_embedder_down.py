from __future__ import annotations

from collections.abc import Sequence

from handoff.embed import EmbedderUnavailable
from handoff.graph.history import handoff_requests
from handoff.mcp.context import ToolContext
from handoff.mcp.record_tools import record_decision
from handoff.mcp.search_tool import search


class DownEmbedder:
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise EmbedderUnavailable("model download failed")

    def embed_query(self, text: str) -> list[float]:
        raise EmbedderUnavailable("model download failed")


def _down(ctx: ToolContext) -> ToolContext:
    return ToolContext(
        graph=ctx.graph, role=ctx.role, cwd=ctx.cwd, now=ctx.now, embedder=DownEmbedder()
    )


def test_decision_is_saved_when_the_model_is_unavailable(frontend: ToolContext) -> None:
    reply = record_decision(_down(frontend), "keep JWT in cookies", "safer", "Auth")
    assert reply.startswith("Recorded decision")
    (request,) = handoff_requests(frontend.graph, role="frontend", since=0)
    assert [d.text for d in request.decisions] == ["keep JWT in cookies"]


def test_search_falls_back_to_words_when_the_model_is_unavailable(
    frontend: ToolContext,
) -> None:
    ctx = _down(frontend)
    record_decision(ctx, "keep JWT in cookies", "safer", "auth")
    assert "keep JWT in cookies" in search(ctx, "JWT")
