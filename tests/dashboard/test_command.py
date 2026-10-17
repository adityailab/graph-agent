from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from falkordb import Graph

from handoff.config import Config
from handoff.dashboard.server import make_server
from handoff.graph.messages import claim_pending_messages
from handoff.graph.needs import open_needs


@pytest.fixture
def base(config: Config, two_sessions: Graph, tmp_path: Path) -> Iterator[str]:
    server = make_server(config, port=0, folder=tmp_path)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _post(
    url: str, payload: Any, content_type: str = "application/json"
) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": content_type},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"{}")


def test_a_message_typed_in_the_dock_reaches_the_session(base: str, two_sessions: Graph) -> None:
    status, body = _post(
        base + "/api/command", {"kind": "msg", "to": "Backend", "text": "use paise"}
    )
    assert status == 200
    assert "Sent to backend" in body["reply"]
    got = claim_pending_messages(two_sessions, session_id="be", role="backend", since=0, at=10**15)
    assert [(m.from_role, m.text) for m in got] == [("person", "use paise")]


def test_a_need_typed_in_the_dock_is_open_for_that_role(base: str, two_sessions: Graph) -> None:
    status, body = _post(base + "/api/command", {"kind": "need", "to": "backend", "text": "a CDN"})
    assert status == 200
    assert "backend" in body["reply"]
    assert ("person", "a CDN") in [
        (who, text) for _, who, text in open_needs(two_sessions, "backend")
    ]


def test_a_message_to_a_role_with_no_session_says_so(base: str) -> None:
    _, body = _post(base + "/api/command", {"kind": "msg", "to": "qa", "text": "hi"})
    assert "No session has the role qa yet" in body["reply"]


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "rm", "to": "backend", "text": "x"},
        {"kind": "msg", "to": "", "text": "x"},
        {"kind": "msg", "to": "backend", "text": "  "},
        {"kind": "msg", "to": "backend", "text": "x" * 5000},
        {"kind": "msg", "to": 3, "text": "x"},
    ],
)
def test_a_command_that_makes_no_sense_is_refused(base: str, payload: dict[str, Any]) -> None:
    assert _post(base + "/api/command", payload)[0] == 400


def test_a_command_must_be_json_so_a_web_page_cannot_post_one_blindly(base: str) -> None:
    status, _ = _post(
        base + "/api/command", {"kind": "msg", "to": "backend", "text": "x"}, "text/plain"
    )
    assert status == 415
