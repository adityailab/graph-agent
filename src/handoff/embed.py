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
    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class FastEmbedder:
    """An Embedder backed by fastembed, with the model cached under `cache_dir`."""

    def __init__(self, *, cache_dir: Path) -> None:
        self._cache_dir = cache_dir
        self._model: Any = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per text."""
        if not texts:
            return []
        if self._model is None:
            from fastembed import TextEmbedding  # slow import, so only when needed

            self._cache_dir.mkdir(parents=True, exist_ok=True)
            self._model = TextEmbedding(MODEL_NAME, cache_dir=str(self._cache_dir))
        return [[float(x) for x in vector] for vector in self._model.embed(list(texts))]
