"""Turning text into vectors for FalkorDB's vector index.

FalkorDB stores and searches vectors but does not compute them, so a small local
model does. It loads once, in the long-lived MCP server (warmed in the background at
start), never in a hook. When it cannot load, callers carry on without vectors.
"""

from __future__ import annotations

import contextlib
import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Protocol

MODEL_NAME = "BAAI/bge-small-en-v1.5"  # 384 dimensions, matches schema.EMBED_DIM


class EmbedderUnavailable(Exception):  # noqa: N818 - reads as a state, like StandinUnavailable
    """The embedding model could not be loaded or run."""


class Embedder(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Vectors for stored text: decisions, topic names."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """A vector for a search question, matched against stored text."""
        ...


class FastEmbedder:
    """An Embedder backed by fastembed, with the model cached under `cache_dir`."""

    def __init__(self, *, cache_dir: Path, loader: Callable[[], Any] | None = None) -> None:
        self._cache_dir = cache_dir
        self._loader = loader or self._load_fastembed
        self._model: Any = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def _load_fastembed(self) -> Any:
        from fastembed import TextEmbedding  # slow import, so only when needed

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        return TextEmbedding(MODEL_NAME, cache_dir=str(self._cache_dir))

    def _ready(self) -> Any:
        with self._lock:
            if self._model is None:
                try:
                    self._model = self._loader()
                except Exception as exc:
                    # fastembed and onnxruntime raise many types (network, disk, runtime);
                    # all mean the same thing to callers.
                    raise EmbedderUnavailable(f"embedding model unavailable: {exc}") from exc
            return self._model

    def warm_up(self) -> threading.Thread:
        """Load the model in the background so the first tool call does not wait."""

        def load() -> None:
            # A failure here is reported by the first real call instead.
            with contextlib.suppress(EmbedderUnavailable):
                self._ready()

        thread = threading.Thread(target=load, name="embedder-warm-up", daemon=True)
        thread.start()
        return thread

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per stored text."""
        if not texts:
            return []
        model = self._ready()
        try:
            return [[float(x) for x in v] for v in model.passage_embed(list(texts))]
        except Exception as exc:  # same reasoning as in _ready
            raise EmbedderUnavailable(f"embedding failed: {exc}") from exc

    def embed_query(self, text: str) -> list[float]:
        """Return a question's vector. BGE models expect a retrieval prefix on queries,
        which fastembed's query_embed adds; without it questions match poorly."""
        model = self._ready()
        try:
            (vector,) = model.query_embed([text])
        except Exception as exc:  # same reasoning as in _ready
            raise EmbedderUnavailable(f"embedding failed: {exc}") from exc
        return [float(x) for x in vector]
