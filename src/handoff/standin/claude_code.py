"""Calling Claude through Claude Code itself, on the person's existing login.

No API key: `claude -p` runs headless with no tools, settings or MCP servers, from a
temporary folder, so it cannot trigger this project's own hooks.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile

from handoff.standin.answer import StandinUnavailable

DEFAULT_MODEL = "opus"
TIMEOUT_SECONDS = 90


class ClaudeCodeClient:
    """A ModelClient backed by `claude -p --output-format json`."""

    def __init__(self, *, binary: str = "claude", model: str | None = None) -> None:
        self.binary = binary
        self.model = model or os.environ.get("HANDOFF_STANDIN_MODEL") or DEFAULT_MODEL

    def _command(self, system: str) -> list[str]:
        return [
            self.binary, "-p", "--output-format", "json", "--model", self.model,
            "--tools", "", "--setting-sources", "", "--strict-mcp-config",
            "--no-session-persistence", "--system-prompt", system,
        ]  # fmt: skip

    def complete(self, system: str, user: str) -> str:
        """Return the model's reply text. Raises StandinUnavailable on any failure."""
        try:
            with tempfile.TemporaryDirectory() as scratch:
                done = subprocess.run(  # noqa: S603 - fixed argv, no shell
                    self._command(system),
                    input=user,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_SECONDS,
                    cwd=scratch,
                    check=False,
                )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise StandinUnavailable(f"claude could not run: {type(exc).__name__}") from exc
        if done.returncode != 0:
            raise StandinUnavailable(f"claude exited with code {done.returncode}")
        try:
            result = json.loads(done.stdout)
        except json.JSONDecodeError as exc:
            raise StandinUnavailable("claude returned unreadable output") from exc
        if not isinstance(result, dict) or result.get("is_error") or "result" not in result:
            raise StandinUnavailable("claude reported an error")
        return str(result["result"])
