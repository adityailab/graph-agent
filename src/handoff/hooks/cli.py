"""The `handoff-hook` command that Claude Code runs for each hook event.

It never blocks a session: every error is logged and the exit code is 0.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from handoff import spool
from handoff.config import Config, resolve_role
from handoff.graph.connection import connect
from handoff.hooks.dispatch import HookOutput, apply_event
from handoff.hooks.prepare import prepare_hook_input
from handoff.ids import now_ms

log = logging.getLogger("handoff.hooks")
_OUTAGE = (RedisConnectionError, RedisTimeoutError)


def is_outage(exc: Exception) -> bool:
    """True when the database could not be reached, as opposed to a bad query or event."""
    return isinstance(exc, _OUTAGE)


def _setup_logging(config: Config) -> None:
    logs = config.home / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=logs / "hooks.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _read_event(stdin: str, env: Mapping[str, str]) -> dict[str, Any]:
    data = json.loads(stdin)
    # The project folder, not the shell's current folder: the agent may `cd`, and the
    # MCP server finds this session again by role and project folder.
    project_dir = str(Path(env.get("CLAUDE_PROJECT_DIR") or str(data.get("cwd", ""))).resolve())
    prepared = prepare_hook_input(data, project_dir) | {"cwd": project_dir}
    return {"input": prepared, "role": resolve_role(project_dir, env), "at": now_ms()}


def _apply(config: Config, event: dict[str, Any]) -> HookOutput:
    try:
        graph = connect(config)
        replayed = spool.replay(
            config.home, lambda saved: apply_event(graph, saved), is_outage=is_outage
        )
        if replayed.pending:
            # Older events are still waiting; applying this one first would break order.
            spool.append(config.home, event)
            return None
        return apply_event(graph, event)
    except _OUTAGE:
        log.warning("database unreachable; event saved for replay")
        spool.append(config.home, event)
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
        _setup_logging(config)
        _emit(_apply(config, _read_event(sys.stdin.read(), os.environ)))
    except Exception:
        # The only broad catch in the project: a hook must never block a session.
        log.exception("hook failed")
    return 0


def run() -> None:
    """Console-script entry point."""
    sys.exit(main())


if __name__ == "__main__":
    run()
