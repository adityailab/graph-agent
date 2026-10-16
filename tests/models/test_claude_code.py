from __future__ import annotations

import pytest

from handoff.models.base import ModelUnavailable
from handoff.models.claude_code import ClaudeCodeClient


def test_missing_claude_binary_is_reported_as_unavailable() -> None:
    with pytest.raises(ModelUnavailable):
        ClaudeCodeClient(binary="/no/such/claude").complete("system", "user")


def test_failing_claude_command_is_reported_as_unavailable() -> None:
    with pytest.raises(ModelUnavailable):
        ClaudeCodeClient(binary="false").complete("system", "user")


def test_child_process_gets_a_clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    from handoff.models.claude_code import child_environment

    monkeypatch.setenv("HANDOFF_ROLE", "backend")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "abc")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/cfg")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    env = child_environment()
    assert "HANDOFF_ROLE" not in env
    assert "CLAUDE_CODE_SESSION_ID" not in env
    assert "ANTHROPIC_API_KEY" not in env
    assert env["CLAUDE_CONFIG_DIR"] == "/cfg"
