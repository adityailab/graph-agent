from __future__ import annotations

import subprocess
from collections.abc import Sequence

from handoff.demo.drive import drive

LISTING = "0 env -i HANDOFF_ROLE=frontend claude\n1 env -i HANDOFF_ROLE=backend claude\n"


class FakeTmux:
    """Panes answer a typed prompt with a new 'done' line."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []
        self.turns = {"hd:demo.0": 0, "hd:demo.1": 0}

    def __call__(self, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        argv, out = list(args), ""
        if argv[1] == "list-panes":
            out = LISTING
        elif argv[1] == "capture-pane":
            out = f"✻ Done for {self.turns[argv[-1]]}s · done 1:00 PM\n> "
        elif argv[1] == "send-keys" and argv[-2] == "-l":
            self.sent.append((argv[3], argv[-1]))
        elif argv[1] == "send-keys" and argv[-1] == "Enter":
            self.turns[argv[3]] += 1
        return subprocess.CompletedProcess(argv, 0, out, "")


def test_each_round_is_sent_and_waited_for() -> None:
    tmux = FakeTmux()
    rounds = ({"frontend": "build it", "backend": "serve it"}, {"backend": "fix it"})
    said: list[str] = []
    assert drive(rounds, session="hd", runner=tmux, sleep=lambda _: None, say=said.append) == 0
    assert tmux.sent == [
        ("hd:demo.0", "build it"),
        ("hd:demo.1", "serve it"),
        ("hd:demo.1", "fix it"),
    ]
    assert any("round 2" in line and "done" in line for line in said)
