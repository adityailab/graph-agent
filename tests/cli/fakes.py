"""A stand-in for running docker and other programs in CLI tests."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence

from handoff.cli.runner import Runner


def fake_runner(
    calls: list[list[str]], outputs: dict[tuple[str, ...], str] | None = None, *, code: int = 0
) -> Runner:
    """Record each argv; answer with the output whose key is a prefix of the argv."""

    def run(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        argv = list(args)
        calls.append(argv)
        out = next(
            (
                text
                for prefix, text in (outputs or {}).items()
                if tuple(argv[: len(prefix)]) == prefix
            ),
            "",
        )
        return subprocess.CompletedProcess(argv, code, out, "")

    return run
