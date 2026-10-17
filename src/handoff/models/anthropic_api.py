"""Calling Claude through the Anthropic API with the official SDK (needs ANTHROPIC_API_KEY)."""

from __future__ import annotations

import os
from typing import Any

from handoff.models.base import ModelUnavailable

DEFAULT_MODEL = "claude-opus-5-5"
MAX_TOKENS = 4096
# On a policy refusal the API re-runs the request on a fallback model it chooses.
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


def sdk_headers() -> dict[str, str]:
    """Extra headers for the SDK: a key that is not scoped to a workspace needs its id
    (ANTHROPIC_WORKSPACE_ID) sent as anthropic-workspace-id."""
    workspace = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
    return {"anthropic-workspace-id": workspace} if workspace else {}


def _explain(exc: Exception) -> str:
    """The API's own explanation when it gave one (it never contains the key)."""
    body = getattr(exc, "body", None)
    detail = body.get("error", {}).get("message") if isinstance(body, dict) else None
    return f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__


class AnthropicClient:
    """A ModelClient backed by `anthropic` (beta messages, for server-side fallbacks)."""

    def __init__(self, *, model: str | None = None, client: Any = None) -> None:
        self.model = model or DEFAULT_MODEL
        self._client = client

    def _sdk(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(default_headers=sdk_headers())
        return self._client

    def complete(self, system: str, user: str) -> str:
        """Return the reply text. Raises ModelUnavailable on errors and refusals."""
        import anthropic

        try:
            response = self._sdk().beta.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": user}],
                betas=[_FALLBACK_BETA],
                fallbacks="default",
                **({"system": system} if system else {}),
            )
        except anthropic.AnthropicError as exc:
            raise ModelUnavailable(f"Anthropic API: {_explain(exc)}") from exc
        if response.stop_reason == "refusal":
            raise ModelUnavailable("the model declined this request")
        if response.stop_reason == "max_tokens":
            raise ModelUnavailable("the reply was cut off at the token limit")
        return "".join(block.text for block in response.content if block.type == "text")
