"""What handoff needs on this machine, and how to fix each thing that is missing."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from handoff.cli.runner import Runner


@dataclass(frozen=True)
class Problem:
    name: str
    fix: str
    optional: bool = False  # handoff still works, with less


_DOCKER_FIX = (
    "Docker is not running. Start it (with Colima: colima start; with Docker Desktop: open "
    "it), or install it from https://docs.docker.com/get-docker/."
)
_CLAUDE_FIX = (
    "Claude Code is not installed: see https://claude.com/claude-code, then run claude once "
    "to log in."
)
_NPX_FIX = (
    "Node.js (npx) is not installed, so FalkorDB's own MCP server is left out; install "
    "Node 18 or later to add it."
)


def _docker_running(runner: Runner) -> bool:
    try:
        return runner(["docker", "info", "--format", "{{.ServerVersion}}"]).returncode == 0
    except (FileNotFoundError, OSError):
        return False


def check_prerequisites(
    runner: Runner, *, which: Callable[[str], str | None], need_docker: bool
) -> list[Problem]:
    """Problems in the order to fix them. Docker is needed only to start the database."""
    problems: list[Problem] = []
    if need_docker and not _docker_running(runner):
        problems.append(Problem("docker", _DOCKER_FIX))
    if which("claude") is None:
        problems.append(Problem("claude", _CLAUDE_FIX))
    if which("npx") is None:
        problems.append(Problem("npx", _NPX_FIX, optional=True))
    return problems
