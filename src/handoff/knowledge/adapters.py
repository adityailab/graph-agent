"""Plugging our model backends and embedder into GraphRAG-SDK."""

from __future__ import annotations

import threading
from typing import Any

from graphrag_sdk import Embedder, LLMInterface
from graphrag_sdk.core.models import LLMResponse

from handoff.embed import MODEL_NAME
from handoff.embed import Embedder as OurEmbedder
from handoff.models.base import ModelClient, ModelUnavailable


class ModelLLM(LLMInterface):
    """Any of our ModelClients (Claude Code, Anthropic API, Ollama) as a GraphRAG LLM.

    GraphRAG sends one prompt; it goes in as the user message with no system text. Keep
    concurrency low for Claude Code: each call starts a `claude -p` process.
    """

    def __init__(self, model: ModelClient, *, name: str, max_concurrency: int = 2) -> None:
        super().__init__(model_name=name, max_concurrency=max_concurrency)
        self._model = model
        self._failures = 0
        self._lock = threading.Lock()

    @property
    def failures(self) -> int:
        """How many calls have failed so far. GraphRAG's extraction swallows model errors,
        so callers compare this before and after an ingest."""
        with self._lock:
            return self._failures

    def invoke(self, prompt: str, **kwargs: Any) -> LLMResponse:
        try:
            return LLMResponse(content=self._model.complete("", prompt))
        except ModelUnavailable:
            with self._lock:
                self._failures += 1
            raise


class EmbedderAdapter(Embedder):
    """Our local embedder as a GraphRAG embedder.

    GraphRAG embeds stored chunks and questions through the same method, so both use the
    stored-text embedding: one consistent space for its own vector indexes.
    """

    def __init__(self, embedder: OurEmbedder) -> None:
        self._embedder = embedder

    @property
    def model_name(self) -> str:
        return MODEL_NAME

    def embed_query(self, text: str, **kwargs: Any) -> list[float]:
        return self._embedder.embed([text])[0]
