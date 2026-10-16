"""Calling a local model through Ollama's HTTP API."""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from typing import Any

from handoff.models.base import ModelUnavailable

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:7b"
TIMEOUT_SECONDS = 120

Post = Callable[[str, dict[str, Any]], dict[str, Any]]


def _http_post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(  # noqa: S310 - the URL is the configured Ollama host
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
        data: dict[str, Any] = json.loads(response.read())
        return data


class OllamaClient:
    """A ModelClient backed by Ollama's `/api/chat`."""

    def __init__(
        self, *, host: str | None = None, model: str | None = None, post: Post | None = None
    ) -> None:
        host = (host or DEFAULT_HOST).rstrip("/")
        # OLLAMA_HOST is often written without a scheme, e.g. "localhost:11434".
        self.host = host if "://" in host else f"http://{host}"
        self.model = model or DEFAULT_MODEL
        self._post = post or _http_post

    def complete(self, system: str, user: str) -> str:
        """Return the reply text. Raises ModelUnavailable when Ollama fails or is down."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": 0},
        }
        try:
            reply = self._post(f"{self.host}/api/chat", payload)
        except (OSError, ValueError) as exc:
            raise ModelUnavailable(f"Ollama at {self.host}: {type(exc).__name__}") from exc
        message = reply.get("message") if isinstance(reply, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise ModelUnavailable("Ollama returned an unexpected reply")
        return content
