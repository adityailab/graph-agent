from __future__ import annotations

from collections.abc import Callable
from typing import Any

from falkordb import Graph

from handoff.graph.decisions import add_decision
from handoff.hooks.dispatch import apply_event
from handoff.hooks.prepare import prepare_hook_input

HookJson = Callable[[str], dict[str, Any]]


def _apply(graph: Graph, raw: dict[str, Any], at: int = 10) -> Any:
    event = {"input": prepare_hook_input(raw, "/work/app"), "role": "frontend", "at": at}
    return apply_event(graph, event, live=True)


def test_stop_is_blocked_once_when_edits_have_no_decision(
    graph: Graph, hook_json: HookJson
) -> None:
    _apply(graph, hook_json("user_prompt"))
    _apply(graph, hook_json("post_edit"))
    output = _apply(graph, hook_json("stop"))
    assert output["decision"] == "block"
    assert "record_decision" in output["reason"]
    again = _apply(graph, hook_json("stop") | {"stop_hook_active": True})
    assert again is None


def test_stop_is_allowed_once_a_decision_is_recorded(graph: Graph, hook_json: HookJson) -> None:
    _apply(graph, hook_json("user_prompt"))
    _apply(graph, hook_json("post_edit"))
    add_decision(
        graph, request_id="p-test", decision_id="d1", text="t", reason="r", topic="x", at=11
    )
    assert _apply(graph, hook_json("stop")) is None


def test_stop_without_edits_is_allowed(graph: Graph, hook_json: HookJson) -> None:
    _apply(graph, hook_json("user_prompt"))
    assert _apply(graph, hook_json("stop")) is None


def test_replayed_stop_never_blocks(graph: Graph, hook_json: HookJson) -> None:
    _apply(graph, hook_json("user_prompt"))
    _apply(graph, hook_json("post_edit"))
    event = {
        "input": prepare_hook_input(hook_json("stop"), "/work/app"),
        "role": "frontend",
        "at": 12,
    }
    assert apply_event(graph, event, live=False) is None


def test_stop_without_prompt_id_checks_the_latest_request(
    graph: Graph, hook_json: HookJson
) -> None:
    _apply(graph, hook_json("user_prompt"))
    _apply(graph, hook_json("post_edit"))
    stop = hook_json("stop")
    del stop["prompt_id"]
    assert _apply(graph, stop)["decision"] == "block"


def test_stop_for_an_unrecorded_prompt_checks_the_latest_request(
    graph: Graph, hook_json: HookJson
) -> None:
    _apply(graph, hook_json("user_prompt"))
    _apply(graph, hook_json("post_edit"))
    assert _apply(graph, hook_json("stop") | {"prompt_id": "p-unknown"})["decision"] == "block"
