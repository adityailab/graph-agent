"""Turning text into vectors for FalkorDB's vector index.

FalkorDB stores and searches vectors but does not compute them, so a small local
model does. It loads on first use and only in the long-lived MCP server, never in a
hook, because loading takes seconds.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

MODEL_NAME = "BAAI/bge-small-en-v1.5"  # 384 dimensions, matches schema.EMBED_DIM


class Embedder(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Vectors for stored text: decisions, topic names."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """A vector for a search question, matched against stored text."""
        ...


class FastEmbedder:
    """An Embedder backed by fastembed, with the model cached under `cache_dir`."""

    def __init__(self, *, cache_dir: Path) -> None:
        self._cache_dir = cache_dir
        self._model: Any = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def _ready(self) -> Any:
        if self._model is None:
            from fastembed import TextEmbedding  # slow import, so only when needed

            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._model = TextEmbedding(MODEL_NAME, cache_dir=str(self._cache_dir))
        return self._model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per stored text."""
        if not texts:
            return []
        return [[float(x) for x in v] for v in self._ready().passage_embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        """Return a question's vector. BGE models expect a retrieval prefix on queries,
        which fastembed's query_embed adds; without it questions match poorly."""
        (vector,) = self._ready().query_embed([text])
        return [float(x) for x in vector]
