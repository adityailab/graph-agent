from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("graphrag_sdk")

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
