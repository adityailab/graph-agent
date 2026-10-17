"""Running other programs (docker, tmux, claude). One function, so tests can replace it."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence

Runner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]


def run_command(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Run a program without a shell and capture its output. Raises FileNotFoundError
    when the program is not installed."""
    return subprocess.run(  # noqa: S603 - argv lists built by handoff, no shell
        list(args), capture_output=True, text=True, timeout=120, check=False
    )
