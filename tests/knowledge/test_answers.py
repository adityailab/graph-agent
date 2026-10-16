from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from falkordb import Graph

pytest.importorskip("graphrag_sdk")

from handoff.knowledge.answers import answer_question, find_concepts


class FakeRag:
    def completion_sync(self, question: str, **kwargs: Any) -> Any:
        section = SimpleNamespace(
            content="## Key Entities\n- avatarUrl: avatar field\n- CDN_URL: cdn setting",
            metadata={"section": "entities"},
        )
        return SimpleNamespace(
            answer="Frontend reads avatarUrl; backend adds it.",
            retriever_result=SimpleNamespace(items=[section]),
        )


def test_answer_lists_the_work_it_drew_on(kg: Graph, backend_with_decision: Graph) -> None:
    text = answer_question(FakeRag(), kg, backend_with_decision, "Who needs avatarUrl?")
    assert text.startswith("Frontend reads avatarUrl; backend adds it.")
    assert 'frontend decision d1: "read avatarUrl"' in text
    assert 'backend request p9: "add avatarUrl to the API"' in text


def test_concepts_show_which_sessions_mention_them(kg: Graph, backend_with_decision: Graph) -> None:
    text = find_concepts(kg, backend_with_decision, "avatarUrl")
    first = text.splitlines()[1]
    assert first.startswith("avatarUrl (Concept):")
    assert "frontend decision d1" in first
    assert "backend request p9" in first


def test_unknown_concept_says_so(kg: Graph, backend_with_decision: Graph) -> None:
    assert find_concepts(kg, backend_with_decision, "kubernetes") == (
        "No concepts in the knowledge graph match."
    )


def test_entity_names_without_descriptions_or_with_colons_are_read() -> None:
    from handoff.knowledge.answers import _key_entities

    section = SimpleNamespace(
        content="## Key Entities\n- std::string: a type\n- CDN_URL\n",
        metadata={"section": "entities"},
    )
    result = SimpleNamespace(retriever_result=SimpleNamespace(items=[section]))
    assert _key_entities(result) == ["std::string", "CDN_URL"]
