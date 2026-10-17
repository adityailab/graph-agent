"""A GraphRAG instance with its own event loop, and failures we can see."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from falkordb import Graph
from graphrag_sdk import Entity, GraphExtraction, GraphRAG, GraphRAGError

from handoff.graph.knowledge import merge_same_name_entities
from handoff.knowledge.adapters import ModelLLM
from handoff.knowledge.runner import AsyncRunner
from handoff.models.base import ModelUnavailable

TIMEOUT_SECONDS = 300
_BOUNDARIES = "software projects: code, infrastructure and delivery work"


class KnowledgeUnavailable(ModelUnavailable):
    """The knowledge graph could not answer or ingest (model or database trouble)."""


class KnowledgeClient:
    """Synchronous calls on one GraphRAG instance, all through one event loop."""

    def __init__(self, *, rag: GraphRAG, llm: ModelLLM, extractor: GraphExtraction, kg: Graph):
        self.rag, self.kg = rag, kg
        self._llm, self._extractor = llm, extractor
        self._runner = AsyncRunner()

    def _call(self, coro: Any) -> Any:
        try:
            return self._runner.run(coro, timeout=TIMEOUT_SECONDS)
        except GraphRAGError as exc:
            raise KnowledgeUnavailable(f"knowledge graph: {exc}") from exc

    def ingest_sync(self, *, text: str, document_id: str) -> None:
        """Ingest one item. Raises KnowledgeUnavailable, after removing the partial
        document, if any model call failed during extraction."""
        failures = self._llm.failures
        self._call(self.rag.ingest(text=text, document_id=document_id, extractor=self._extractor))
        if self._llm.failures > failures:
            self._call(self.rag.delete_document(document_id, if_missing="ignore"))
            raise KnowledgeUnavailable("the model failed while extracting; will retry later")

    def known_labels(self) -> list[str]:
        """The entity types in the ontology GraphRAG-SDK has committed."""
        return [e.label for e in self._call(self.rag.get_ontology()).entities]

    def suggest_types(self, texts: list[str]) -> list[tuple[str, str]]:
        """Entity types the given texts mention that the ontology lacks, as proposed by
        GraphRAG-SDK (it reads files, so the texts are written to a temporary folder)."""
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for n, text in enumerate(texts):
                path = Path(tmp) / f"item{n}.txt"
                path.write_text(text)
                paths.append(str(path))
            proposal = self._call(self.rag.suggest_schema_extensions(paths, boundaries=_BOUNDARIES))
        return [(e.label, e.description or "") for e in proposal.new_entities]

    def add_types(self, types: list[tuple[str, str]]) -> None:
        """Add entity types for future extraction; existing entities are untouched."""
        for label, description in types:
            self._call(self.rag.add_entity(Entity(label=label, description=description)))

    def finalize_sync(self) -> None:
        """Run GraphRAG's post-ingest steps (including its exact same-name, same-type merge),
        then merge same-named entities across types (ours). No fuzzy merge: similar names
        are often different things (Checkout.tsx and Checkout.test.tsx)."""
        self._call(self.rag.finalize())
        merge_same_name_entities(self.kg)

    def completion_sync(self, question: str, **kwargs: Any) -> Any:
        return self._call(self.rag.completion(question, **kwargs))

    def close(self) -> None:
        self._runner.close()
