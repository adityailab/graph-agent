from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("graphrag_sdk")

from graphrag_sdk import GraphExtraction
from graphrag_sdk.core.context import Context
from graphrag_sdk.core.models import TextChunk, TextChunks

from handoff.knowledge.adapters import ModelLLM
from handoff.knowledge.extractor import HANDOFF_ENTITY_TYPES, WorkExtractor, handoff_ontology


class RecordingLLM:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def ainvoke(self, prompt: str, **kwargs: Any) -> SimpleNamespace:
        self.prompts.append(prompt)
        return SimpleNamespace(content="[]")


def test_extraction_is_told_to_skip_the_assistants_own_mechanics() -> None:
    llm = RecordingLLM()
    extractor = WorkExtractor(llm)  # type: ignore[arg-type]
    asyncio.run(extractor.extract_entities("Use the ask tool", ["Concept"], "c1"))
    prompt = llm.prompts[0]
    assert "Use the ask tool" in prompt
    assert "Do NOT extract the AI assistant's own tools" in prompt


def test_the_ontology_names_kinds_of_software_work() -> None:
    labels = [e.label for e in handoff_ontology().entities]
    assert labels == list(HANDOFF_ENTITY_TYPES)
    assert {"API", "DataField", "Component", "Concept"} <= set(labels)


class RecordingModel:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def complete(self, system: str, user: str) -> str:
        self.prompts.append(user)
        return "[]"


def test_graphrags_own_pipeline_sends_our_guidance() -> None:
    """GraphRAG-SDK batches prompts itself for LLMExtractor subclasses, skipping
    extract_entities; this drives its real extraction to prove the guidance arrives."""
    model = RecordingModel()
    llm = ModelLLM(model, name="fake", max_concurrency=1)
    extraction = GraphExtraction(llm, entity_extractor=WorkExtractor(llm), max_concurrency=1)
    chunks = TextChunks(chunks=[TextChunk(text="Use the ask tool on Checkout.tsx", index=0)])
    asyncio.run(extraction.extract(chunks, handoff_ontology(), Context()))
    ner = [p for p in model.prompts if "Use the ask tool on Checkout.tsx" in p]
    assert ner, model.prompts
    assert "Do NOT extract the AI assistant's own tools" in ner[0]
    assert "a field, column, key" in ner[0]  # the types arrive with their meanings
