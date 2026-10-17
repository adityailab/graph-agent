from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator

import pytest
from falkordb import Graph

from handoff.config import Config
from handoff.dashboard.server import make_server


@pytest.fixture
def base(config: Config, two_sessions: Graph) -> Iterator[str]:
    server = make_server(config, port=0, clock=lambda: 300)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _get(url: str, host: str | None = None) -> tuple[int, str, dict[str, str]]:
    request = urllib.request.Request(url, headers={"Host": host} if host else {})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read().decode(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, "", {}


def test_the_page_and_its_assets_are_served(base: str) -> None:
    for path in ("/", "/app.js", "/style.css"):
        status, body, headers = _get(base + path)
        assert status == 200
        assert body
        assert "default-src 'self'" in headers["Content-Security-Policy"]


def test_the_state_is_json_of_the_graph(base: str) -> None:
    status, body, _ = _get(base + "/api/state")
    assert status == 200
    assert {r["role"] for r in json.loads(body)["roles"]} == {"frontend", "backend"}


def test_unknown_paths_are_not_found(base: str) -> None:
    assert _get(base + "/../pyproject.toml")[0] == 404
    assert _get(base + "/nope")[0] == 404


def test_a_foreign_host_name_is_refused(base: str) -> None:
    """Stops a web page on another site from reading the graph through DNS rebinding."""
    assert _get(base + "/api/state", host="evil.example")[0] == 403


def test_only_the_ask_box_accepts_a_post(base: str) -> None:
    request = urllib.request.Request(base + "/api/state", data=b"{}", method="POST")
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(request, timeout=5)
    assert caught.value.code == 404


def test_a_kind_of_memory_opens_into_its_items(base: str) -> None:
    status, body, _ = _get(base + "/api/memory/episodic")
    assert status == 200
    assert {"request", "edit"} <= {i["title"] for i in json.loads(body)["items"]}


def test_relevant_memories_come_for_a_role(base: str) -> None:
    status, body, _ = _get(base + "/api/memory/relevant/backend")
    assert status == 200
    assert "items" in json.loads(body)


def test_an_unknown_kind_of_memory_is_not_found(base: str) -> None:
    assert _get(base + "/api/memory/dreams")[0] == 404


def test_a_kind_of_memory_can_be_fetched_as_a_graph(base: str) -> None:
    status, body, _ = _get(base + "/api/memory/semantic/graph")
    assert status == 200
    graph = json.loads(body)
    assert {"Decision", "Topic"} <= {n["kind"] for n in graph["nodes"]}
    assert graph["edges"]


def test_an_unknown_kind_has_no_graph(base: str) -> None:
    assert _get(base + "/api/memory/dreams/graph")[0] == 404


def _post(url: str, payload: object, *, content_type: str = "application/json") -> tuple[int, dict]:  # type: ignore[type-arg]
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": content_type}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        text = exc.read()
        return exc.code, json.loads(text) if text.startswith(b"{") else {}


@pytest.fixture
def asking(config: Config, two_sessions: Graph) -> Iterator[str]:
    def fake(
        question: str,
        config: Config,
        history: list[tuple[str, str]],
        progress: Callable[[str, str], None] | None = None,
    ) -> tuple[str, list[str]]:
        if progress:
            progress("step", "thinking")
            progress("text", "let me look")
            progress("step", "running Cypher: MATCH (n)")
        if question == "boom":
            raise TimeoutError
        return f"answer to {question} after {len(history)} turns", ["MATCH (n) RETURN n"]

    server = make_server(config, port=0, asker=fake)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def test_a_question_gets_an_answer_and_the_cypher_that_made_it(asking: str) -> None:
    status, body = _post(asking + "/api/ask", {"question": "who decided what?"})
    assert status == 200
    assert body == {
        "answer": "answer to who decided what? after 0 turns",
        "queries": ["MATCH (n) RETURN n"],
    }


def test_an_empty_or_huge_question_is_refused(asking: str) -> None:
    assert _post(asking + "/api/ask", {"question": "  "})[0] == 400
    assert _post(asking + "/api/ask", {"question": "x" * 2000})[0] == 400


def test_a_question_must_be_json_so_a_web_page_cannot_post_one_blindly(asking: str) -> None:
    status, _ = _post(
        asking + "/api/ask", b'{"question": "hi"}', content_type="application/x-www-form-urlencoded"
    )
    assert status == 415


def test_a_failed_ask_is_reported_not_raised(asking: str) -> None:
    status, body = _post(asking + "/api/ask", {"question": "boom"})
    assert status == 502
    assert "error" in body


def test_other_posts_are_not_found(asking: str) -> None:
    assert _post(asking + "/api/nope", {})[0] == 404


def test_earlier_turns_reach_the_asker_and_only_the_recent_ones(asking: str) -> None:
    turns = [{"q": f"q{i}", "a": f"a{i}"} for i in range(20)]
    status, body = _post(asking + "/api/ask", {"question": "next", "history": turns})
    assert status == 200
    assert "after 6 turns" in body["answer"]


def test_a_malformed_history_is_refused(asking: str) -> None:
    assert _post(asking + "/api/ask", {"question": "x", "history": "nope"})[0] == 400
    assert _post(asking + "/api/ask", {"question": "x", "history": [{"q": 1}]})[0] == 400


def _stream(url: str, payload: object) -> list[dict]:  # type: ignore[type-arg]
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        assert response.headers["Content-Type"].startswith("application/x-ndjson")
        return [json.loads(line) for line in response.read().decode().splitlines() if line]


def test_a_streamed_ask_sends_each_step_then_the_answer(asking: str) -> None:
    lines = _stream(asking + "/api/ask", {"question": "hi", "stream": True})
    assert [x["step"] for x in lines if "step" in x] == ["thinking", "running Cypher: MATCH (n)"]
    assert {"text": "let me look"} in lines
    assert lines[-1] == {"answer": "answer to hi after 0 turns", "queries": ["MATCH (n) RETURN n"]}


def test_a_streamed_ask_that_fails_ends_with_an_error_line(asking: str) -> None:
    lines = _stream(asking + "/api/ask", {"question": "boom", "stream": True})
    assert "error" in lines[-1]


def test_a_common_question_is_answered_without_the_model(asking: str) -> None:
    status, body = _post(asking + "/api/ask", {"question": "Who has read whose work?"})
    assert status == 200
    assert "No session has read" in body["answer"]  # from the graph, not the fake model
    assert body["queries"] == []
    assert body["quick"]


def test_a_follow_up_goes_to_the_model_even_if_it_sounds_common(asking: str) -> None:
    turns = [{"q": "earlier", "a": "something"}]
    _, body = _post(
        asking + "/api/ask", {"question": "which rules are in force?", "history": turns}
    )
    assert body["answer"].startswith("answer to")


def test_a_streamed_quick_answer_says_no_model_was_used(asking: str) -> None:
    lines = _stream(asking + "/api/ask", {"question": "which rules are in force?", "stream": True})
    assert any("without a model" in x.get("step", "") for x in lines)
    assert lines[-1]["quick"]
