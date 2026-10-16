"""The `handoff-hook` command that Claude Code runs for each hook event.

`handoff-hook` handles one event from stdin; `handoff-hook wait` runs the background
waiter (see waiter.py). Neither ever blocks a session: errors are logged, exit is 0.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from collections.abc import Mapping
from typing import Any

from handoff import spool
from handoff.config import Config
from handoff.graph.connection import connect
from handoff.hooks import generation, waiter
from handoff.hooks.dispatch import HookOutput, apply_event
from handoff.hooks.identity import project_and_role
from handoff.hooks.logs import OUTAGE, is_outage, setup_logging
from handoff.hooks.prepare import prepare_hook_input
from handoff.ids import now_ms

log = logging.getLogger("handoff.hooks")


def _read_event(stdin: str, env: Mapping[str, str]) -> dict[str, Any]:
    data = json.loads(stdin)
    project_dir, role = project_and_role(data, env)
    prepared = prepare_hook_input(data, project_dir) | {"cwd": project_dir}
    return {"input": prepared, "role": role, "at": now_ms()}


def _worth_saving(event: dict[str, Any]) -> bool:
    """Only events that record something are saved: a Stop or a tool call that edited
    nothing would only register the session again when replayed."""
    hook = event["input"]
    if hook.get("hook_event_name") == "Stop":
        return False
    return not (hook.get("hook_event_name") == "PostToolUse" and not hook.get("edit_path"))


def _save(config: Config, event: dict[str, Any]) -> None:
    if _worth_saving(event):
        spool.append(config.home, event)


def _apply(config: Config, event: dict[str, Any]) -> HookOutput:
    if event["input"].get("hook_event_name") == "UserPromptSubmit":
        # A new turn: any running waiter for this session stands down.
        generation.bump(config.home, str(event["input"]["session_id"]))
    try:
        graph = connect(config)
        replayed = spool.replay(
            config.home, lambda saved: apply_event(graph, saved, live=False), is_outage=is_outage
        )
        if replayed.pending:
            # Older events are still waiting; applying this one first would break order.
            _save(config, event)
            return None
        return apply_event(graph, event, live=True)
    except OUTAGE:
        log.warning("database unreachable; event saved for replay if it records anything")
        _save(config, event)
        return None


def _emit(output: HookOutput) -> None:
    if isinstance(output, dict):
        print(json.dumps(output))
    elif output:
        print(output)


def main() -> int:
    """Handle one hook event from stdin. Always returns 0."""
    try:
        config = Config.from_env()
        setup_logging(config)
        _emit(_apply(config, _read_event(sys.stdin.read(), os.environ)))
    except Exception:
        # The only broad catch in the project: a hook must never block a session.
        log.exception("hook failed")
    return 0


def run() -> None:
    """Console-script entry point."""
    if sys.argv[1:2] == ["wait"]:
        sys.exit(waiter.main(sys.stdin.read(), os.environ))
    sys.exit(main())


if __name__ == "__main__":
    run()
