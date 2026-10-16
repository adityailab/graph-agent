from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from typing import Any

import pytest
from falkordb import Graph

from handoff.config import Config
from handoff.graph.messages import add_message, claim_pending_messages
from handoff.graph.schema import ensure_schema
from handoff.graph.sessions import upsert_session
from handoff.ids import now_ms

STOP_INPUT = json.dumps(
    {"hook_event_name": "Stop", "session_id": "fe", "cwd": "/work/app", "stop_hook_active": False}
)


@pytest.fixture
def sessions(graph: Graph) -> Graph:
    ensure_schema(graph)
    upsert_session(graph, session_id="fe", role="frontend", cwd="/work/app", at=now_ms())
    upsert_session(graph, session_id="be", role="backend", cwd="/work/app", at=now_ms())
    return graph


def _waiter(config: Config, *, wait: float, port: int | None = None) -> subprocess.Popen[str]:
    env = os.environ | {
        "HANDOFF_GRAPH": config.graph_name,
        "HANDOFF_HOME": str(config.home),
        "HANDOFF_DB_PORT": str(port or config.port),
        "HANDOFF_ROLE": "frontend",
        "CLAUDE_PROJECT_DIR": "/work/app",
        "HANDOFF_WAIT_SECONDS": str(wait),
        "HANDOFF_WAIT_POLL": "0.2",
        "CLAUDE_CODE_SESSION_ATTENDED": "1",
    }
    proc = subprocess.Popen(
        [sys.executable, "-m", "handoff.hooks.cli", "wait"],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )
    assert proc.stdin is not None
    proc.stdin.write(STOP_INPUT)
    proc.stdin.close()
    return proc


def _send(graph: Graph, text: str) -> None:
    add_message(
        graph,
        message_id=text,
        from_session_id="be",
        to_role="frontend",
        kind="message",
        text=text,
        reply_to=None,
        at=now_ms(),
    )


def test_waiting_message_wakes_the_session(config: Config, sessions: Graph) -> None:
    _send(sessions, "avatarUrl is live")
    proc = _waiter(config, wait=10)
    assert proc.wait(timeout=20) == 2
    assert proc.stderr is not None
    assert "avatarUrl is live" in proc.stderr.read()
    assert (
        claim_pending_messages(sessions, session_id="fe", role="frontend", since=0, at=now_ms())
        == []
    )


def test_message_arriving_while_waiting_wakes_the_session(config: Config, sessions: Graph) -> None:
    proc = _waiter(config, wait=15)
    time.sleep(1.5)
    assert proc.poll() is None
    _send(sessions, "deploy needs CDN_URL")
    assert proc.wait(timeout=10) == 2


def test_no_message_ends_quietly(config: Config, sessions: Graph) -> None:
    assert _waiter(config, wait=1).wait(timeout=20) == 0


def test_second_waiter_for_a_session_exits_at_once(config: Config, sessions: Graph) -> None:
    locks = config.home / "locks"
    locks.mkdir(parents=True)
    with (locks / "fe.lock").open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        start = time.monotonic()
        assert _waiter(config, wait=30).wait(timeout=20) == 0
        assert time.monotonic() - start < 10


def test_database_down_ends_quietly(config: Config) -> None:
    assert _waiter(config, wait=1, port=1).wait(timeout=20) == 0


def test_newer_waiter_takes_over_from_an_older_one(config: Config, sessions: Graph) -> None:
    old = _waiter(config, wait=30)
    time.sleep(1.0)
    new = _waiter(config, wait=30)
    assert old.wait(timeout=10) == 0
    _send(sessions, "for the newer waiter")
    assert new.wait(timeout=10) == 2


def test_new_prompt_stops_a_running_waiter(
    config: Config, sessions: Graph, hook_json: Callable[[str], dict[str, Any]]
) -> None:
    proc = _waiter(config, wait=30)
    time.sleep(1.0)
    env = os.environ | {
        "HANDOFF_GRAPH": config.graph_name,
        "HANDOFF_HOME": str(config.home),
        "HANDOFF_ROLE": "frontend",
        "CLAUDE_PROJECT_DIR": "/work/app",
    }
    prompt = hook_json("user_prompt") | {"session_id": "fe", "cwd": "/work/app"}
    subprocess.run(
        [sys.executable, "-m", "handoff.hooks.cli"],
        input=json.dumps(prompt),
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=True,
    )
    assert proc.wait(timeout=10) == 0


def test_unattended_session_gets_no_waiter(config: Config, sessions: Graph) -> None:
    _send(sessions, "would wake an attended session")
    env = os.environ | {
        "HANDOFF_GRAPH": config.graph_name,
        "HANDOFF_HOME": str(config.home),
        "HANDOFF_ROLE": "frontend",
        "CLAUDE_PROJECT_DIR": "/work/app",
        "CLAUDE_CODE_SESSION_ATTENDED": "0",
    }
    start = time.monotonic()
    done = subprocess.run(
        [sys.executable, "-m", "handoff.hooks.cli", "wait"],
        input=STOP_INPUT,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert done.returncode == 0
    assert time.monotonic() - start < 5
    assert (
        len(
            claim_pending_messages(sessions, session_id="fe", role="frontend", since=0, at=now_ms())
        )
        == 1
    )
