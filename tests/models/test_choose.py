from __future__ import annotations

from handoff.models.anthropic_api import AnthropicClient
from handoff.models.choose import model_from_env
from handoff.models.claude_code import ClaudeCodeClient
from handoff.models.ollama import OllamaClient


def test_claude_code_is_the_default() -> None:
    assert isinstance(model_from_env({}), ClaudeCodeClient)


def test_backends_are_chosen_by_name() -> None:
    assert isinstance(model_from_env({"HANDOFF_MODEL": "ollama"}), OllamaClient)
    anthropic = model_from_env({"HANDOFF_MODEL": "Anthropic", "ANTHROPIC_API_KEY": "sk-x"})
    assert isinstance(anthropic, AnthropicClient)


def test_model_name_can_be_overridden() -> None:
    client = model_from_env({"HANDOFF_MODEL": "ollama", "HANDOFF_MODEL_NAME": "llama3.2:3b"})
    assert isinstance(client, OllamaClient)
    assert client.model == "llama3.2:3b"


def test_unknown_backend_falls_back_to_claude_code() -> None:
    assert isinstance(model_from_env({"HANDOFF_MODEL": "gpt"}), ClaudeCodeClient)
