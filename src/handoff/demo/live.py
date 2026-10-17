"""Setting up the live demo: a scratch project whose sessions need no permission prompts
for handoff's own tools, and the tmux grid; then the driver runs in the background."""

from __future__ import annotations

import contextlib
import getpass
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from handoff.cli.runner import Runner
from handoff.config import Config
from handoff.demo.tmux import layout_commands
from handoff.install import install


def prepare_workspace(folder: Path, config: Config, *, bin_dir: Path) -> None:
    """Install handoff on the demo graph, pre-approve our tools, and use Haiku in the
    background (stand-in answers, knowledge)."""
    install(folder, bin_dir=bin_dir, config=config, falkordb_mcp=False, graph=config.graph_name)
    path = folder / ".claude" / "settings.local.json"
    settings = json.loads(path.read_text())
    settings["env"].update(HANDOFF_HOME=str(config.home), HANDOFF_MODEL_NAME="haiku")
    settings["permissions"] = {"allow": ["mcp__handoff"]}
    settings["enableAllProjectMcpServers"] = True
    path.write_text(json.dumps(settings, indent=2) + "\n")


def start_grid(session: str, folder: Path, runner: Runner, *, model: str) -> None:
    """Replace any old demo session with a fresh grid."""
    runner(["tmux", "kill-session", "-t", session])
    for cmd in layout_commands(
        session,
        str(folder),
        path=os.environ.get("PATH", "/usr/bin:/bin"),
        home=str(Path.home()),
        user=getpass.getuser(),
        handoff_bin=str(Path(sys.executable).parent / "handoff"),
        model=model,
    ):
        runner(cmd)


def stop_previous_driver(state: Path) -> None:
    """Stop the driver of an earlier run, which would keep typing into the new grid."""
    pid_file = state / "driver.pid"
    try:
        pid = int(pid_file.read_text())
    except (OSError, ValueError):
        return
    pid_file.unlink(missing_ok=True)
    with contextlib.suppress(ProcessLookupError):  # already finished
        os.kill(pid, signal.SIGTERM)


def start_driver(session: str, state: Path) -> None:
    """Run `handoff demo --drive` detached, so this terminal can attach to the grid. Its pid
    and log live in handoff's own state folder, outside the scratch project that is reset."""
    state.mkdir(parents=True, exist_ok=True)
    stop_previous_driver(state)
    with (state / "driver.log").open("w") as out:
        proc = subprocess.Popen(  # noqa: S603 - our own command, no shell
            [str(Path(sys.executable).parent / "handoff"), "demo", "--drive", "--session", session],
            stdout=out,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    (state / "driver.pid").write_text(str(proc.pid))


def launch(
    session: str, folder: Path, config: Config, runner: Runner, *, model: str, manual: bool
) -> str:
    """Build the grid in `folder` (driven in the background unless `manual`); return what to
    tell the person."""
    prepare_workspace(folder, config, bin_dir=Path(sys.executable).parent)
    stop_previous_driver(config.home / "demo")
    start_grid(session, folder, runner, model=model)
    if not manual:
        start_driver(session, config.home / "demo")
    then = "then type your own prompts." if manual else "the rounds then start by themselves."
    return (
        f"Live demo in {folder}, graph {config.graph_name}. Attach with: tmux attach -t "
        f"{session}. Accept the folder-trust prompt in each Claude pane; {then}"
    )
