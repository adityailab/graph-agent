"""Running other programs (docker, tmux, claude). One function, so tests can replace it."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence

Runner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]


_PULL_SECONDS = 1800  # a first image pull on a slow link


def _timeout(args: Sequence[str]) -> int:
    return _PULL_SECONDS if list(args)[:2] == ["docker", "pull"] else 120


def run_command(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Run a program without a shell and capture its output. Raises FileNotFoundError
    when the program is not installed."""
    return subprocess.run(  # noqa: S603 - argv lists built by handoff, no shell
        list(args), capture_output=True, text=True, timeout=_timeout(args), check=False
    )
