"""Calling Claude through the Anthropic API with the official SDK (needs ANTHROPIC_API_KEY)."""

from __future__ import annotations

from typing import Any

from handoff.models.base import ModelUnavailable

DEFAULT_MODEL = "claude-opus-5-5"
MAX_TOKENS = 4096
# On a policy refusal the API re-runs the request on a fallback model it chooses.
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicClient:
    """A ModelClient backed by `anthropic` (beta messages, for server-side fallbacks)."""

    def __init__(self, *, model: str | None = None, client: Any = None) -> None:
        self.model = model or DEFAULT_MODEL
        self._client = client

    def _sdk(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def complete(self, system: str, user: str) -> str:
        """Return the reply text. Raises ModelUnavailable on errors and refusals."""
        import anthropic

        try:
            response = self._sdk().beta.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user}],
                betas=[_FALLBACK_BETA],
                fallbacks="default",
            )
        except anthropic.AnthropicError as exc:
            raise ModelUnavailable(f"Anthropic API: {type(exc).__name__}") from exc
        if response.stop_reason == "refusal":
            raise ModelUnavailable("the model declined this request")
        return "".join(block.text for block in response.content if block.type == "text")
