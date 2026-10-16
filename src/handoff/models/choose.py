"""Choosing the model backend from the environment.

HANDOFF_MODEL: "claude-code" (default; the person's Claude Code login, no key),
"anthropic" (needs ANTHROPIC_API_KEY) or "ollama" (local; OLLAMA_HOST optional).
HANDOFF_MODEL_NAME overrides the backend's default model.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from handoff.models.anthropic_api import AnthropicClient
from handoff.models.base import ModelClient
from handoff.models.claude_code import ClaudeCodeClient
from handoff.models.ollama import OllamaClient

log = logging.getLogger(__name__)


def model_from_env(env: Mapping[str, str]) -> ModelClient:
    """Return the configured backend; unknown names fall back to Claude Code."""
    backend = env.get("HANDOFF_MODEL", "claude-code").strip().lower()
    name = env.get("HANDOFF_MODEL_NAME") or env.get("HANDOFF_STANDIN_MODEL") or None
    if backend == "anthropic":
        return AnthropicClient(model=name)
    if backend == "ollama":
        return OllamaClient(host=env.get("OLLAMA_HOST"), model=name)
    if backend not in ("claude-code", "claude_code", ""):
        log.warning("unknown HANDOFF_MODEL %r; using claude-code", backend)
    return ClaudeCodeClient(model=name)
