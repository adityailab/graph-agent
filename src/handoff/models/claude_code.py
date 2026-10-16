"""Calling Claude through Claude Code itself, on the person's existing login.

No API key: `claude -p` runs headless with no tools, settings or MCP servers, from a
temporary folder, so it cannot trigger this project's own hooks.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile

from handoff.models.base import ModelUnavailable

DEFAULT_MODEL = "opus"  # Claude Code's alias for its current Opus model
TIMEOUT_SECONDS = 90


# How Claude Code itself logs in and where its settings live; the child needs these.
_LOGIN_VARIABLES = frozenset(
    {
        "CLAUDE_CONFIG_DIR",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
        "CLAUDE_CODE_USE_FOUNDRY",
    }
)


def child_environment() -> dict[str, str]:
    """The environment for a headless `claude`: no handoff or Claude Code session
    variables (it is not part of any session) except how Claude Code logs in, and no
    ANTHROPIC_API_KEY, so it uses the person's Claude Code login rather than billing a key."""
    return {
        k: v
        for k, v in os.environ.items()
        if (not k.startswith(("HANDOFF_", "CLAUDE")) or k in _LOGIN_VARIABLES)
        and k != "ANTHROPIC_API_KEY"
    }


class ClaudeCodeClient:
    """A ModelClient backed by `claude -p --output-format json`."""

    def __init__(self, *, binary: str = "claude", model: str | None = None) -> None:
        self.binary = binary
        self.model = model or DEFAULT_MODEL

    def _command(self, system: str) -> list[str]:
        return [
            self.binary, "-p", "--output-format", "json", "--model", self.model,
            "--tools", "", "--setting-sources", "", "--strict-mcp-config",
            "--no-session-persistence", "--system-prompt", system,
        ]  # fmt: skip

    def complete(self, system: str, user: str) -> str:
        """Return the model's reply text. Raises ModelUnavailable on any failure."""
        try:
            with tempfile.TemporaryDirectory() as scratch:
                done = subprocess.run(  # noqa: S603 - fixed argv, no shell
                    self._command(system),
                    input=user,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_SECONDS,
                    cwd=scratch,
                    env=child_environment(),
                    check=False,
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ModelUnavailable(f"claude could not run: {type(exc).__name__}") from exc
        if done.returncode != 0:
            raise ModelUnavailable(f"claude exited with code {done.returncode}")
        try:
            result = json.loads(done.stdout)
        except json.JSONDecodeError as exc:
            raise ModelUnavailable("claude returned unreadable output") from exc
        if not isinstance(result, dict) or result.get("is_error") or "result" not in result:
            raise ModelUnavailable("claude reported an error")
        return str(result["result"])
