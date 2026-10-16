from __future__ import annotations

from collections.abc import Sequence

from handoff.graph.edits import add_edit
from handoff.graph.schema import EMBED_DIM
from handoff.mcp.context import ToolContext
from handoff.mcp.record_tools import record_decision
from handoff.mcp.search_tool import fuse, search


class KeywordEmbedder:
    """Auth-related texts point one way, layout texts another, everything else a third."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        out = []
        for t in texts:
            low = t.lower()
            if any(w in low for w in ("token", "login", "auth", "session", "jwt")):
                axis = 0
            elif any(w in low for w in ("css", "grid", "layout")):
                axis = 1
            else:
                axis = 2
            vec = [0.0] * EMBED_DIM
            vec[axis] = 1.0
            out.append(vec)
        return out

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


def _with_embedder(ctx: ToolContext) -> ToolContext:
    return ToolContext(
        graph=ctx.graph, role=ctx.role, cwd=ctx.cwd, now=ctx.now, embedder=KeywordEmbedder()
    )


def test_fusion_ranks_items_found_by_both_lists_first() -> None:
    assert fuse([["a", "b"], ["b", "c"]], k=3) == ["b", "a", "c"]


def test_recording_a_decision_stores_its_embedding(frontend: ToolContext) -> None:
    ctx = _with_embedder(frontend)
    record_decision(ctx, "keep JWT in cookies", "safer than localStorage", "auth")
    rows = ctx.graph.query("MATCH (d:Decision) RETURN d.embedding IS NOT NULL").result_set
    assert rows == [[True]]


def test_search_finds_a_paraphrase_and_shows_graph_context(backend: ToolContext) -> None:
    fe = _with_embedder(
        ToolContext(graph=backend.graph, role="frontend", cwd="/w", now=lambda: 2_000)
    )
    add_edit(
        fe.graph, request_id="p1", edit_id="e1", tool="Edit", path="Auth.tsx", summary="", at=1_100
    )
    add_edit(
        fe.graph, request_id="p9", edit_id="e9", tool="Edit", path="Auth.tsx", summary="", at=1_600
    )
    record_decision(fe, "keep JWT in cookies", "safer than localStorage", "auth")
    record_decision(fe, "use css grid", "simpler", "ui")
    text = search(_with_embedder(backend), "how do we handle login sessions?")
    first = text.splitlines()[1]
    assert "keep JWT in cookies" in first
    assert "frontend" in first
    assert "Auth.tsx" in text
    assert "also changed by backend" in text


def test_search_without_matches_says_so(backend: ToolContext) -> None:
    assert search(_with_embedder(backend), "kubernetes") == "No recorded decisions match."


def test_blank_query_is_refused(backend: ToolContext) -> None:
    assert search(_with_embedder(backend), " ") == "Not searched: query is empty."


class QueryAwareEmbedder(KeywordEmbedder):
    """Documents about auth sit on axis 0; only the query-side embedding lands near them."""

    def embed_query(self, text: str) -> list[float]:
        vec = [0.0] * EMBED_DIM
        vec[0] = 1.0
        return vec


def test_search_embeds_the_query_as_a_query(frontend: ToolContext) -> None:
    ctx = ToolContext(
        graph=frontend.graph,
        role=frontend.role,
        cwd=frontend.cwd,
        now=frontend.now,
        embedder=QueryAwareEmbedder(),
    )
    record_decision(ctx, "keep JWT in cookies", "safer than localStorage", "auth")
    assert "keep JWT in cookies" in search(ctx, "zzz unrelated wording")
