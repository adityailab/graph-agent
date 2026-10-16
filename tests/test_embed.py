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


@pytest.mark.skipif(os.environ.get("HANDOFF_LIVE_TESTS") != "1", reason="downloads a model")
def test_live_question_finds_the_relevant_decision(tmp_path: Path) -> None:
    embedder = FastEmbedder(cache_dir=tmp_path)
    stored, unrelated = embedder.embed(
        [
            "Keep the JWT refresh token in an httpOnly cookie; scripts cannot read it.",
            "Use css grid for the profile card layout.",
        ]
    )
    question = embedder.embed_query("where is the auth token stored")
    assert 1 - _cosine(question, stored) < 0.45 < 1 - _cosine(question, unrelated)


def test_failing_model_load_is_reported_as_unavailable(tmp_path: Path) -> None:
    from handoff.embed import EmbedderUnavailable

    def broken() -> object:
        raise OSError("no network")

    embedder = FastEmbedder(cache_dir=tmp_path, loader=broken)
    with pytest.raises(EmbedderUnavailable):
        embedder.embed(["x"])


def test_model_is_loaded_once_even_when_asked_concurrently(tmp_path: Path) -> None:
    import threading
    import time

    loads = []

    class Model:
        def passage_embed(self, texts: list[str]) -> list[list[float]]:
            return [[0.0] * EMBED_DIM for _ in texts]

    def slow_loader() -> Model:
        loads.append(1)
        time.sleep(0.2)
        return Model()

    embedder = FastEmbedder(cache_dir=tmp_path, loader=slow_loader)
    threads = [threading.Thread(target=embedder.embed, args=(["x"],)) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(loads) == 1


def test_warm_up_loads_in_the_background(tmp_path: Path) -> None:
    loaded = []

    def loader() -> object:
        loaded.append(1)
        return object()

    embedder = FastEmbedder(cache_dir=tmp_path, loader=loader)
    embedder.warm_up().join(timeout=5)
    assert loaded == [1]
