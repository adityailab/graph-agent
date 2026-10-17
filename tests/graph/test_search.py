from __future__ import annotations

import pytest
from falkordb import Graph

from handoff.graph.decisions import add_decision, set_decision_embedding
from handoff.graph.edits import add_edit
from handoff.graph.requests import add_request
from handoff.graph.schema import EMBED_DIM, ensure_schema
from handoff.graph.search import (
    decision_hits,
    fulltext_decisions,
    fulltext_query,
    similar_decisions,
)
from handoff.graph.sessions import upsert_session


def _vec(*head: float) -> list[float]:
    return list(head) + [0.0] * (EMBED_DIM - len(head))


@pytest.fixture
def decided(graph: Graph) -> Graph:
    """Frontend decided about JWT cookies in Auth.tsx; backend also edited Auth.tsx."""
    ensure_schema(graph)
    upsert_session(graph, session_id="fe", role="frontend", cwd="/w", at=1)
    upsert_session(graph, session_id="be", role="backend", cwd="/w", at=1)
    add_request(graph, session_id="fe", request_id="p1", text="add login", at=2)
    add_edit(graph, request_id="p1", edit_id="e1", tool="Edit", path="Auth.tsx", summary="", at=3)
    add_decision(
        graph,
        request_id="p1",
        decision_id="d1",
        text="store JWT refresh tokens in cookies",
        reason="safer than localStorage",
        topic="auth",
        at=4,
    )
    set_decision_embedding(graph, "d1", _vec(1.0, 0.0))
    add_request(graph, session_id="fe", request_id="p2", text="style card", at=5)
    add_decision(
        graph,
        request_id="p2",
        decision_id="d2",
        text="use css grid for the card",
        reason="simpler layout",
        topic="ui",
        at=6,
    )
    set_decision_embedding(graph, "d2", _vec(0.0, 1.0))
    add_request(graph, session_id="be", request_id="p3", text="token endpoint", at=7)
    add_edit(graph, request_id="p3", edit_id="e3", tool="Edit", path="Auth.tsx", summary="", at=8)
    return graph


def test_full_text_finds_exact_terms(decided: Graph) -> None:
    assert [d for d, _ in fulltext_decisions(decided, "JWT", k=5)] == ["d1"]


def test_full_text_tolerates_query_syntax_characters(decided: Graph) -> None:
    assert [d for d, _ in fulltext_decisions(decided, 'JWT -"cookies" @|', k=5)] == ["d1"]


def test_vector_search_returns_nearest_first(decided: Graph) -> None:
    hits = similar_decisions(decided, _vec(0.9, 0.1), k=2)
    assert [d for d, _ in hits] == ["d1", "d2"]
    assert hits[0][1] < hits[1][1]  # cosine distance: lower is closer


def test_hits_are_expanded_through_shared_files(decided: Graph) -> None:
    (hit,) = decision_hits(decided, ["d1"])
    assert (hit.role, hit.request_text, hit.files) == ("frontend", "add login", ("Auth.tsx",))
    assert hit.related_roles == ("backend",)


def test_long_words_are_fuzzy_short_words_prefixes_and_tiny_words_dropped() -> None:
    assert fulltext_query("cookes api is ok") == "%cookes% | api*"


def test_a_misspelling_still_finds_the_decision(decided: Graph) -> None:
    assert [d for d, _ in fulltext_decisions(decided, "cookes", k=5)] == ["d1"]


def test_a_prefix_finds_the_longer_word(decided: Graph) -> None:
    assert [d for d, _ in fulltext_decisions(decided, "lay", k=5)] == ["d2"]
