"""Typing the scripted rounds into the live demo's panes and waiting for each to finish."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence

from handoff.cli.runner import Runner
from handoff.demo.tmux import done_line, pane_ready, panes_by_role

ROUND_CAP_SECONDS = 480
POLL_SECONDS = 4.0
TRUST_WAIT_SECONDS = 600


def _screen(runner: Runner, pane: str) -> str:
    return runner(["tmux", "capture-pane", "-p", "-J", "-t", pane]).stdout


def _send(runner: Runner, pane: str, text: str, sleep: Callable[[float], None]) -> None:
    runner(["tmux", "send-keys", "-t", pane, "-l", text])
    sleep(1)
    runner(["tmux", "send-keys", "-t", pane, "Enter"])


def _finished(runner: Runner, pane: str, was: str) -> Callable[[], bool]:
    """A check that this pane's 'done' line differs from `was` (its turn has ended)."""
    return lambda: done_line(_screen(runner, pane)) not in ("", was)


def _wait(check: Callable[[], bool], *, seconds: float, sleep: Callable[[float], None]) -> bool:
    deadline = time.monotonic() + seconds
    while not check():
        if time.monotonic() > deadline:
            return False
        sleep(POLL_SECONDS)
    return True


def drive(
    rounds: Sequence[dict[str, str]],
    *,
    session: str,
    runner: Runner,
    sleep: Callable[[float], None],
    say: Callable[[str], None],
) -> int:
    """Run each round: send every role's prompt, then wait until each pane is done.
    Roles within a round work in parallel."""
    listing = runner(
        ["tmux", "list-panes", "-t", f"{session}:demo", "-F", "#{pane_index} #{pane_start_command}"]
    ).stdout
    panes = panes_by_role(listing, session)
    needed = {role for round_ in rounds for role in round_}
    absent = sorted(needed - set(panes))
    if absent:
        say(f"stopped: no pane found for {', '.join(absent)} (is the grid still open?)")
        return 1
    say("waiting for each Claude pane to be ready (accept the folder-trust prompt if shown)")
    if not _wait(
        lambda: all(pane_ready(_screen(runner, panes[r])) for r in needed),
        seconds=TRUST_WAIT_SECONDS,
        sleep=sleep,
    ):
        say("gave up: the panes were not ready within 10 minutes")
        return 1
    for n, round_ in enumerate(rounds, 1):
        before = {role: done_line(_screen(runner, panes[role])) for role in round_}
        for role, prompt in round_.items():
            _send(runner, panes[role], prompt, sleep)
        for role in round_:
            finished = _wait(
                _finished(runner, panes[role], before[role]),
                seconds=ROUND_CAP_SECONDS,
                sleep=sleep,
            )
            say(f"round {n}: {role} {'done' if finished else 'still working after 8 minutes'}")
    say("all rounds sent")
    return 0
