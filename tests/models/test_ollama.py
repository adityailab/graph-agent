from __future__ import annotations

import os
from typing import Any

import pytest

from handoff.models.base import ModelUnavailable
from handoff.models.ollama import DEFAULT_MODEL, OllamaClient


def test_request_shape_and_reply_text() -> None:
    sent: list[tuple[str, dict[str, Any]]] = []

    def post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        sent.append((url, payload))
        return {"message": {"role": "assistant", "content": "hi"}, "done": True}

    client = OllamaClient(host="http://localhost:11434", post=post)
    assert client.complete("be brief", "hello") == "hi"
    url, payload = sent[0]
    assert url == "http://localhost:11434/api/chat"
    assert payload["model"] == DEFAULT_MODEL
    assert payload["stream"] is False
    assert payload["messages"] == [
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "hello"},
    ]


def test_unreachable_ollama_is_reported_as_unavailable() -> None:
    def post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise OSError("connection refused")

    with pytest.raises(ModelUnavailable):
        OllamaClient(host="http://localhost:1", post=post).complete("s", "u")


def test_malformed_reply_is_reported_as_unavailable() -> None:
    with pytest.raises(ModelUnavailable):
        OllamaClient(post=lambda url, payload: {"oops": 1}).complete("s", "u")


@pytest.mark.skipif(os.environ.get("HANDOFF_LIVE_OLLAMA") != "1", reason="needs ollama running")
def test_live_ollama_answers() -> None:
    assert OllamaClient().complete("Reply with the single word: ok", "go").strip()
