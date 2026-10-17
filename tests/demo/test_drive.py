from __future__ import annotations

import subprocess
from collections.abc import Sequence

import pytest

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
            out = f"Done for {self.turns[argv[-1]]}s · done 1:00 PM\n> \n accept edits on"
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


def test_a_missing_pane_stops_the_driver_with_a_reason() -> None:
    tmux = FakeTmux()
    said: list[str] = []
    rounds = ({"deploy": "ship it"},)
    assert drive(rounds, session="hd", runner=tmux, sleep=lambda _: None, say=said.append) == 1
    assert any("deploy" in line for line in said)


class SameLineTmux:
    """A pane that works for two looks, then shows the very same 'done' line as before."""

    def __init__(self) -> None:
        self.looks_since_enter: int | None = None

    def __call__(self, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        argv, out = list(args), ""
        if argv[1] == "list-panes":
            out = "0 env -i HANDOFF_ROLE=frontend claude\n"
        elif argv[1] == "send-keys" and argv[-1] == "Enter":
            self.looks_since_enter = 0
        elif argv[1] == "capture-pane":
            idle = "Cooked for 7s \u00b7 done 1:00 PM\n> \n accept edits on"
            if self.looks_since_enter is None:
                out = idle
            else:
                self.looks_since_enter += 1
                out = (
                    "\u2722 Crunching\u2026 (3s \u00b7 \u2193 1k tokens)"
                    if self.looks_since_enter <= 2
                    else idle
                )
        return subprocess.CompletedProcess(argv, 0, out, "")


def test_a_turn_ending_with_the_same_done_line_is_still_noticed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("handoff.demo.drive.ROUND_CAP_SECONDS", 2)
    said: list[str] = []
    drive(
        ({"frontend": "go"},),
        session="hd",
        runner=SameLineTmux(),
        sleep=lambda _: None,
        say=said.append,
    )
    assert any("round 1: frontend done" in line for line in said)
