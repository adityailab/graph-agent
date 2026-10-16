from __future__ import annotations

import math
import os
from pathlib import Path

import pytest

from handoff.embed import MODEL_NAME, FastEmbedder
from handoff.graph.schema import EMBED_DIM


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def test_model_is_not_loaded_until_first_use(tmp_path: Path) -> None:
    embedder = FastEmbedder(cache_dir=tmp_path)
    assert not embedder.loaded
    assert MODEL_NAME == "BAAI/bge-small-en-v1.5"


def test_no_texts_need_no_model(tmp_path: Path) -> None:
    embedder = FastEmbedder(cache_dir=tmp_path)
    assert embedder.embed([]) == []
    assert not embedder.loaded


@pytest.mark.skipif(os.environ.get("HANDOFF_LIVE_TESTS") != "1", reason="downloads a model")
def test_live_paraphrases_are_closer_than_unrelated_text(tmp_path: Path) -> None:
    auth, login, css = FastEmbedder(cache_dir=tmp_path).embed(
        ["auth tokens expire hourly", "login tokens refresh every hour", "css grid layout"]
    )
    assert len(auth) == EMBED_DIM
    assert _cosine(auth, login) > _cosine(auth, css) + 0.2
