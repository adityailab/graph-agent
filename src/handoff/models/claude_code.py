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


def child_environment() -> dict[str, str]:
    """The environment for the stand-in's `claude`: no handoff or Claude Code session
    variables (it is not part of any session), and no ANTHROPIC_API_KEY, so it uses the
    person's Claude Code login rather than billing an API key."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("HANDOFF_", "CLAUDE")) and k != "ANTHROPIC_API_KEY"
    }
    if "CLAUDE_CONFIG_DIR" in os.environ:
        env["CLAUDE_CONFIG_DIR"] = os.environ["CLAUDE_CONFIG_DIR"]
    return env


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
