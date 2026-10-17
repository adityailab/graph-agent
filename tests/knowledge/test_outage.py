"""With the real GraphRAG-SDK extraction: a model outage must not mark work as ingested."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest
from falkordb import FalkorDB, Graph

pytest.importorskip("graphrag_sdk")

from handoff.config import Config, knowledge_graph_name
from handoff.graph.requests import add_request
from handoff.knowledge.startup import build_knowledge_client
from handoff.knowledge.worker import KnowledgeWorker
from handoff.models.base import ModelUnavailable


class DownModel:
    def complete(self, system: str, user: str) -> str:
        raise ModelUnavailable("rate limited")


class FlatEmbedder:
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[1.0] + [0.0] * 383 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [1.0] + [0.0] * 383


def test_outage_leaves_the_item_unmarked_and_the_document_removed(
    ready: Graph, config: Config, tmp_path: Path
) -> None:
    add_request(ready, session_id="s1", request_id="p1", text="add the avatarUrl field", at=10)
    client = build_knowledge_client(config, DownModel(), FlatEmbedder())
    try:
        worker = KnowledgeWorker(graph=ready, rag=client, home=tmp_path)
        assert worker.step() is False
        assert ready.query("MATCH (r:Request {id: 'p1'}) RETURN r.kg_at").result_set == [[None]]
        docs = client.kg.query("MATCH (d:Document {id: 'p1'}) RETURN count(d)").result_set
        assert docs == [[0]]
    finally:
        client.close()
        client.kg.delete()
        # GraphRAG-SDK keeps its ontology in a companion graph of its own.
        FalkorDB(host=config.host, port=config.port).select_graph(
            f"{knowledge_graph_name(config)}__ontology"
        ).delete()
