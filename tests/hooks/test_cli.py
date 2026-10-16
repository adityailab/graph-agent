from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from typing import Any

from falkordb import Graph

from handoff.config import Config

HookJson = Callable[[str], dict[str, Any]]


def _run_hook(
    config: Config, stdin: str, *, port: int | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ | {
        "HANDOFF_GRAPH": config.graph_name,
        "HANDOFF_HOME": str(config.home),
        "HANDOFF_DB_PORT": str(port or config.port),
        "HANDOFF_ROLE": "frontend",
        "CLAUDE_PROJECT_DIR": "/work/app",
    }
    return subprocess.run(
        [sys.executable, "-m", "handoff.hooks.cli"],
        input=stdin,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _request_texts(graph: Graph) -> list[str]:
    return [
        str(r[0]) for r in graph.query("MATCH (r:Request) RETURN r.text ORDER BY r.at").result_set
    ]


def test_prompt_is_recorded_and_nothing_is_printed(
    config: Config, graph: Graph, hook_json: HookJson
) -> None:
    result = _run_hook(config, json.dumps(hook_json("user_prompt") | {"prompt": "hello"}))
    assert (result.returncode, result.stdout) == (0, "")
    assert _request_texts(graph) == ["hello"]


def test_database_down_saves_the_event_and_exits_cleanly(
    config: Config, hook_json: HookJson
) -> None:
    result = _run_hook(config, json.dumps(hook_json("user_prompt")), port=1)
    assert result.returncode == 0
    assert (config.home / "spool.jsonl").read_text().count("\n") == 1


def test_saved_events_are_replayed_once_the_database_is_back(
    config: Config, graph: Graph, hook_json: HookJson
) -> None:
    first = hook_json("user_prompt") | {"prompt": "while down", "prompt_id": "p-down"}
    _run_hook(config, json.dumps(first), port=1)
    second = hook_json("user_prompt") | {"prompt": "after", "prompt_id": "p-up"}
    _run_hook(config, json.dumps(second))
    assert _request_texts(graph) == ["while down", "after"]
    assert (config.home / "spool.jsonl").read_text() == ""


def test_unreadable_input_is_logged_and_exits_cleanly(config: Config) -> None:
    result = _run_hook(config, "{not json")
    assert result.returncode == 0
    assert "hook failed" in (config.home / "logs" / "hooks.log").read_text()
