from __future__ import annotations

from collections.abc import Sequence

import pytest

pytest.importorskip("graphrag_sdk")

from handoff.knowledge.adapters import EmbedderAdapter, ModelLLM
from handoff.models.base import ModelUnavailable


class EchoModel:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return f"echo: {user}"


class DownModel:
    def complete(self, system: str, user: str) -> str:
        raise ModelUnavailable("down")


class TinyEmbedder:
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float(len(t)), 1.0] for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0, 0.0]


def test_model_answers_graphrag_prompts() -> None:
    model = EchoModel()
    llm = ModelLLM(model, name="claude-code", max_concurrency=1)
    assert llm.invoke("extract entities").content == "echo: extract entities"
    assert model.calls == [("", "extract entities")]


def test_model_failure_reaches_graphrag_as_an_error() -> None:
    with pytest.raises(ModelUnavailable):
        ModelLLM(DownModel(), name="x").invoke("p")


def test_embedder_adapter_uses_stored_text_vectors_both_ways() -> None:
    adapter = EmbedderAdapter(TinyEmbedder())
    assert adapter.model_name == "BAAI/bge-small-en-v1.5"
    assert adapter.embed_query("abcd") == [4.0, 1.0]
