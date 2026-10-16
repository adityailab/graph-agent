from __future__ import annotations

import fcntl
import json
import os
import stat
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
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


def test_saved_events_are_private_and_hold_no_raw_tool_output(
    config: Config, hook_json: HookJson
) -> None:
    raw = hook_json("post_edit") | {"tool_response": {"originalFile": "secret body"}}
    _run_hook(config, json.dumps(raw), port=1)
    spool_file = config.home / "spool.jsonl"
    assert stat.S_IMODE(spool_file.stat().st_mode) == 0o600
    assert "secret body" not in spool_file.read_text()


def test_live_event_queues_while_another_hook_replays(
    config: Config, graph: Graph, hook_json: HookJson
) -> None:
    _run_hook(config, json.dumps(hook_json("user_prompt") | {"prompt_id": "p-old"}), port=1)
    env = os.environ | {
        "HANDOFF_GRAPH": config.graph_name,
        "HANDOFF_HOME": str(config.home),
        "HANDOFF_ROLE": "frontend",
    }
    with (config.home / "spool.lock").open("a") as lock:
        # Another hook is mid-replay for 3 seconds.
        fcntl.flock(lock, fcntl.LOCK_EX)
        proc = subprocess.Popen(
            [sys.executable, "-m", "handoff.hooks.cli"], stdin=subprocess.PIPE, env=env, text=True
        )
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(hook_json("user_prompt") | {"prompt_id": "p-new"}))
        proc.stdin.close()
        time.sleep(3)
        fcntl.flock(lock, fcntl.LOCK_UN)
    assert proc.wait(timeout=30) == 0
    assert _request_texts(graph) == []
    assert (config.home / "spool.jsonl").read_text().count("\n") == 2


def test_edit_reaches_the_graph_through_the_command(
    config: Config, graph: Graph, hook_json: HookJson
) -> None:
    _run_hook(config, json.dumps(hook_json("user_prompt")))
    _run_hook(config, json.dumps(hook_json("post_edit")))
    rows = graph.query("MATCH (:Edit)-[:TOUCHED]->(f:File) RETURN f.path").result_set
    assert rows == [["hello.txt"]]


def test_bad_configuration_still_exits_cleanly(config: Config, hook_json: HookJson) -> None:
    env = os.environ | {"HANDOFF_DB_PORT": "not-a-port", "HANDOFF_HOME": str(config.home)}
    result = subprocess.run(
        [sys.executable, "-m", "handoff.hooks.cli"],
        input=json.dumps(hook_json("user_prompt")),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0


def test_session_is_stored_under_the_project_folder_not_the_shell_folder(
    config: Config, graph: Graph, hook_json: HookJson
) -> None:
    raw = hook_json("user_prompt") | {"cwd": "/work/app/src/deep"}
    env = os.environ | {
        "HANDOFF_GRAPH": config.graph_name,
        "HANDOFF_HOME": str(config.home),
        "CLAUDE_PROJECT_DIR": "/work/app",
    }
    env.pop("HANDOFF_ROLE", None)
    subprocess.run(
        [sys.executable, "-m", "handoff.hooks.cli"],
        input=json.dumps(raw),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    rows = graph.query("MATCH (s:Session) RETURN s.cwd, s.role").result_set
    assert rows == [["/work/app", "app"]]


def test_session_folder_is_stored_resolved(
    config: Config, graph: Graph, hook_json: HookJson, tmp_path: Path
) -> None:
    real = tmp_path / "proj"
    real.mkdir()
    link = tmp_path / "proj-link"
    link.symlink_to(real)
    env = os.environ | {
        "HANDOFF_GRAPH": config.graph_name,
        "HANDOFF_HOME": str(config.home),
        "CLAUDE_PROJECT_DIR": str(link),
        "HANDOFF_ROLE": "frontend",
    }
    subprocess.run(
        [sys.executable, "-m", "handoff.hooks.cli"],
        input=json.dumps(hook_json("user_prompt")),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    assert graph.query("MATCH (s:Session) RETURN s.cwd").result_set == [[str(real.resolve())]]
