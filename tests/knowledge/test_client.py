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


def test_finalizing_merges_duplicates_of_every_kind(kg: Graph) -> None:
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
    assert [name for name, _ in rag.calls] == ["finalize", "deduplicate_entities"]
    assert rag.calls[1][1]["fuzzy"] is True
    count = kg.query("MATCH (e:__Entity__) WHERE toLower(e.name) = 'avatarurl' RETURN count(e)")
    assert count.result_set == [[1]]
