from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

import pytest

from handoff.models.anthropic_api import DEFAULT_MODEL, AnthropicClient
from handoff.models.base import ModelUnavailable


class FakeMessages:
    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response, self.error = response, error
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def _client(messages: FakeMessages) -> AnthropicClient:
    fake = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return AnthropicClient(client=fake)


def _response(text: str, stop: str = "end_turn") -> Any:
    return SimpleNamespace(
        stop_reason=stop,
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text=text),
        ],
    )


def test_request_uses_opus_with_server_side_fallbacks() -> None:
    messages = FakeMessages(_response("hi"))
    assert _client(messages).complete("be brief", "hello") == "hi"
    call = messages.calls[0]
    assert call["model"] == DEFAULT_MODEL == "claude-opus-5-5"
    assert call["system"] == "be brief"
    assert call["messages"] == [{"role": "user", "content": "hello"}]
    assert call["fallbacks"] == "default"
    assert call["betas"] == ["server-side-fallback-2026-07-01"]


def test_refusal_is_reported_as_unavailable() -> None:
    with pytest.raises(ModelUnavailable):
        _client(FakeMessages(_response("", stop="refusal"))).complete("s", "u")


def test_api_errors_are_reported_as_unavailable() -> None:
    import anthropic

    error = anthropic.APIConnectionError(request=SimpleNamespace())  # type: ignore[arg-type]
    with pytest.raises(ModelUnavailable):
        _client(FakeMessages(error=error)).complete("s", "u")


@pytest.mark.skipif(
    os.environ.get("HANDOFF_LIVE_TESTS") != "1" or not os.environ.get("ANTHROPIC_API_KEY"),
    reason="calls the Anthropic API",
)
def test_live_anthropic_answers() -> None:
    assert AnthropicClient().complete("Reply with the single word: ok", "go").strip()


def test_empty_system_prompt_is_left_out() -> None:
    messages = FakeMessages(_response("hi"))
    _client(messages).complete("", "hello")
    assert "system" not in messages.calls[0]


def test_cut_off_reply_is_reported_as_unavailable() -> None:
    with pytest.raises(ModelUnavailable):
        _client(FakeMessages(_response('{"answer": ', stop="max_tokens"))).complete("s", "u")


def test_the_apis_own_explanation_is_in_the_error() -> None:
    import anthropic
    import httpx2 as httpx  # the SDK's own HTTP client library

    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(400, request=request)
    error = anthropic.BadRequestError(
        "bad",
        response=response,
        body={
            "type": "error",
            "error": {"type": "invalid_request_error", "message": "this key needs a workspace id"},
        },
    )
    with pytest.raises(ModelUnavailable, match="this key needs a workspace id"):
        _client(FakeMessages(error=error)).complete("s", "u")


def test_a_configured_workspace_is_sent_as_a_header(monkeypatch: pytest.MonkeyPatch) -> None:
    from handoff.models.anthropic_api import sdk_headers

    monkeypatch.setenv("ANTHROPIC_WORKSPACE_ID", "wrkspc_123")
    assert sdk_headers() == {"anthropic-workspace-id": "wrkspc_123"}
    monkeypatch.delenv("ANTHROPIC_WORKSPACE_ID")
    assert sdk_headers() == {}
