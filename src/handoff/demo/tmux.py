"""The live demo's tmux grid, and reading Claude Code's screen in each pane.

Claude Code draws in the alternate screen, which keeps no scrollback: its latest
'for 8s · done 12:29 PM' line replaces the previous one, so a turn has finished when that
line's text changes (counting such lines does not work).
"""

from __future__ import annotations

import re
import shlex

SESSION = "handoff-demo"
ROLES = ("frontend", "deploy", "backend")
_DONE = re.compile(r"for \d+(?:m \d+)?s · done[^\n]*")
_WORKING = re.compile(r"\u2026 \(\d+(?:m \d+)?s \u00b7")  # "Crunching\u2026 (9s \u00b7 ..."
_INPUT_BOX = re.compile(r"^\u2500{10,}\n[\u276f>]\s", re.MULTILINE)  # rule, then the prompt line
_ROLE = re.compile(r"^(\d+) .*HANDOFF_ROLE=(\w+)")


def _clean_env(*, home: str, user: str, path: str) -> str:
    # A clean environment: nothing from the shell that started the demo leaks in.
    return (
        f"env -i HOME={shlex.quote(home)} USER={shlex.quote(user)} LOGNAME={shlex.quote(user)} "
        f"SHELL=/bin/zsh PATH={shlex.quote(path)} TERM=xterm-256color LANG=en_US.UTF-8"
    )


def layout_commands(
    session: str, folder: str, *, path: str, home: str, user: str, handoff_bin: str, model: str
) -> list[list[str]]:
    """tmux commands for a 2x2 grid: three Claude Code sessions and handoff watch."""
    env = _clean_env(home=home, user=user, path=path)
    claude = [
        f"{env} HANDOFF_ROLE={r} claude --model {model} --permission-mode acceptEdits"
        for r in ROLES
    ]
    window = f"{session}:demo"
    cmds = [
        [
            "tmux",
            "new-session",
            "-d",
            "-s",
            session,
            "-x",
            "240",
            "-y",
            "66",
            "-n",
            "demo",
            "-c",
            folder,
            claude[0],
        ],
        ["tmux", "set", "-t", session, "remain-on-exit", "on"],
        ["tmux", "set", "-t", session, "mouse", "on"],
    ]
    for start in (*claude[1:], f"{env} {handoff_bin} watch"):
        cmds += [
            ["tmux", "split-window", "-t", window, "-c", folder, start],
            ["tmux", "select-layout", "-t", window, "tiled"],
        ]
    return cmds


def done_line(screen: str) -> str:
    """The newest 'for 8s · done ...' line on a pane's screen, or '' if none."""
    found = _DONE.findall(screen)
    return found[-1] if found else ""


def trust_pending(screen: str) -> bool:
    """True while Claude Code asks whether to trust the folder (the person answers it)."""
    return "Yes, I trust this folder" in screen


def panes_by_role(listing: str, session: str) -> dict[str, str]:
    """Map each role to its pane, from tmux list-panes with the format
    '#{pane_index} #{pane_start_command}'."""
    panes = {}
    for line in listing.splitlines():
        match = _ROLE.match(line.strip())
        if match:
            panes[match.group(2)] = f"{session}:demo.{match.group(1)}"
    return panes


def pane_ready(screen: str) -> bool:
    """True once Claude Code shows its input and is not asking about trust. Typing earlier
    would land in the trust dialog, or be lost while Claude starts. The input box is the
    signal: a custom status line can replace the 'accept edits on' line."""
    if trust_pending(screen):
        return False
    return "accept edits on" in screen or _INPUT_BOX.search(screen) is not None


def working(screen: str) -> bool:
    """True while Claude Code shows its working spinner ("Crunching… (9s · ↓ 1k tokens)")."""
    return _WORKING.search(screen) is not None
