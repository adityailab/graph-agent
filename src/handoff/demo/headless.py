"""Running one demo session: headless Claude Code in the scratch project, as a role."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from pathlib import Path

from handoff.config import Config
from handoff.demo.script import TOOLS
from handoff.models.claude_code import child_environment

SESSION_TIMEOUT = 300


def session_command(prompt: str, workspace: Path, *, model: str) -> list[str]:
    """claude -p with the workspace's own hooks (settings) and MCP servers."""
    return [
        "claude",
        "-p",
        prompt,
        "--permission-mode",
        "acceptEdits",
        "--setting-sources",
        "local",
        "--strict-mcp-config",
        "--mcp-config",
        str(workspace / ".mcp.json"),
        "--allowedTools",
        *TOOLS,
        "--no-session-persistence",
        "--model",
        model,
    ]


def session_env(role: str, config: Config, *, base: Mapping[str, str]) -> dict[str, str]:
    """The role and handoff's home; no HANDOFF_GRAPH, so the graph comes only from the
    workspace's settings, as it does for a real user. One knowledge worker runs later."""
    env = {k: v for k, v in base.items() if not k.startswith("HANDOFF_")}
    env.update(
        HANDOFF_ROLE=role,
        HANDOFF_HOME=str(config.home),
        HANDOFF_KNOWLEDGE="off",
        HANDOFF_WAIT_SECONDS="3",
        HANDOFF_MODEL_NAME="haiku",
    )
    return env


def run_session(role: str, prompt: str, workspace: Path, config: Config, *, model: str) -> str:
    """Run one session to completion and return its reply."""
    done = subprocess.run(  # noqa: S603 - fixed argv, no shell
        session_command(prompt, workspace, model=model),
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=SESSION_TIMEOUT,
        check=False,
        stdin=subprocess.DEVNULL,
        env=session_env(role, config, base=child_environment()),
    )
    return (done.stdout or done.stderr).strip()
