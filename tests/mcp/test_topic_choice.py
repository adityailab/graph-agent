from __future__ import annotations

from collections.abc import Sequence

from handoff.graph.edits import add_edit
from handoff.graph.schema import EMBED_DIM
from handoff.mcp.context import ToolContext
from handoff.mcp.topic_choice import choose_topic

# name -> (x, y): auth-ish topics near each other, layout far away.
POINTS = {
    "auth tokens": (1.0, 0.0),
    "login tokens": (0.99, 0.12),  # very close: same subject
    "login sessions": (0.8, 0.6),  # distance 0.20: still the same subject (measured up to 0.23)
    "session handling": (0.73, 0.683),  # distance 0.27: related, not the same
    "css layout": (0.0, 1.0),
}


class PointEmbedder:
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        far = [0.0, 0.0, 1.0] + [0.0] * (EMBED_DIM - 3)  # any other text: far from all
        return [list(POINTS[t]) + [0.0] * (EMBED_DIM - 2) if t in POINTS else far for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


def _ctx(base: ToolContext) -> ToolContext:
    return ToolContext(
        graph=base.graph, role=base.role, cwd=base.cwd, now=base.now, embedder=PointEmbedder()
    )


def test_new_topic_is_kept_as_given(frontend: ToolContext) -> None:
    assert choose_topic(_ctx(frontend), "auth tokens", request_id="p1") == "auth tokens"


def test_near_duplicate_reuses_the_existing_topic(frontend: ToolContext) -> None:
    ctx = _ctx(frontend)
    choose_topic(ctx, "auth tokens", request_id="p1")
    assert choose_topic(ctx, "login tokens", request_id="p1") == "auth tokens"


def test_wording_up_to_the_top_of_the_measured_same_subject_range_is_one_topic(
    frontend: ToolContext,
) -> None:
    ctx = _ctx(frontend)
    choose_topic(ctx, "auth tokens", request_id="p1")
    assert choose_topic(ctx, "login sessions", request_id="p1") == "auth tokens"


def _frontend_decided_on_auth(backend: ToolContext) -> None:
    from handoff.mcp.record_tools import record_decision

    fe = _ctx(ToolContext(graph=backend.graph, role="frontend", cwd="/w", now=lambda: 2_000))
    add_edit(
        fe.graph, request_id="p1", edit_id="e1", tool="Edit", path="Auth.tsx", summary="", at=1_100
    )
    record_decision(fe, "keep JWT in cookies", "safer", "auth tokens")


def test_related_topic_without_shared_files_stays_separate(backend: ToolContext) -> None:
    _frontend_decided_on_auth(backend)
    assert choose_topic(_ctx(backend), "session handling", request_id="p9") == ("session handling")


def test_related_topic_is_reused_when_the_work_shares_files(backend: ToolContext) -> None:
    _frontend_decided_on_auth(backend)
    add_edit(
        backend.graph,
        request_id="p9",
        edit_id="e9",
        tool="Edit",
        path="Auth.tsx",
        summary="",
        at=1_600,
    )
    assert choose_topic(_ctx(backend), "session handling", request_id="p9") == "auth tokens"


def test_unrelated_topic_stays_separate(frontend: ToolContext) -> None:
    ctx = _ctx(frontend)
    choose_topic(ctx, "auth tokens", request_id="p1")
    assert choose_topic(ctx, "css layout", request_id="p1") == "css layout"


def test_without_an_embedder_names_are_only_normalised(frontend: ToolContext) -> None:
    assert choose_topic(frontend, "  Auth   Tokens ", request_id="p1") == "auth tokens"
