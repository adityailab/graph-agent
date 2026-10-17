from __future__ import annotations

from typing import Any

import pytest
from falkordb import Graph

pytest.importorskip("graphrag_sdk")

from handoff.knowledge.client import KnowledgeClient


class FakeRag:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def finalize(self) -> None:
        self.calls.append(("finalize", {}))

    async def deduplicate_entities(self, **kwargs: Any) -> int:
        self.calls.append(("deduplicate_entities", kwargs))
        return 0


def test_finalizing_merges_same_named_entities_but_nothing_fuzzy(kg: Graph) -> None:
    kg.query(
        "MATCH (c:Chunk {text: 'a'}) CREATE (:__Entity__:Technology {name: 'avatarurl', "
        "description: 'x'})-[:MENTIONED_IN]->(c)"
    )
    rag = FakeRag()
    client = KnowledgeClient(rag=rag, llm=None, extractor=None, kg=kg)  # type: ignore[arg-type]
    try:
        client.finalize_sync()
    finally:
        client.close()
    # No fuzzy pass: name embeddings put Checkout.tsx and Checkout.test.tsx at 0.945 and
    # getUser and getUsers at 0.941, so it would merge different files and functions.
    assert [name for name, _ in rag.calls] == ["finalize"]
    count = kg.query("MATCH (e:__Entity__) WHERE toLower(e.name) = 'avatarurl' RETURN count(e)")
    assert count.result_set == [[1]]


def test_similar_but_different_names_are_not_merged(kg: Graph) -> None:
    kg.query(
        "MATCH (c:Chunk {text: 'a'}) "
        "CREATE (:__Entity__:File {name: 'Checkout.tsx'})-[:MENTIONED_IN]->(c), "
        "(:__Entity__:File {name: 'Checkout.test.tsx'})-[:MENTIONED_IN]->(c)"
    )
    client = KnowledgeClient(rag=FakeRag(), llm=None, extractor=None, kg=kg)  # type: ignore[arg-type]
    try:
        client.finalize_sync()
    finally:
        client.close()
    rows = kg.query("MATCH (e:File) RETURN e.name ORDER BY e.name").result_set
    assert rows == [["Checkout.test.tsx"], ["Checkout.tsx"]]
