from __future__ import annotations

from collections.abc import Callable
from typing import Any

from falkordb import Graph

from handoff.graph.edits import why_file
from handoff.graph.requests import latest_request_id
from handoff.graph.schema import ensure_schema
from handoff.hooks.events import on_post_tool_use, on_user_prompt
from handoff.hooks.hook_input import HookInput, parse_hook_input
from handoff.hooks.prepare import prepare_hook_input

HookJson = Callable[[str], dict[str, Any]]


def _hook(raw: dict[str, Any]) -> HookInput:
    return parse_hook_input(prepare_hook_input(raw, "/work/app"))


def _prompt(graph: Graph, hook_json: HookJson, **changes: Any) -> None:
    on_user_prompt(graph, _hook(hook_json("user_prompt") | changes), role="frontend", at=10)


def _edit(graph: Graph, hook_json: HookJson, **changes: Any) -> None:
    on_post_tool_use(graph, _hook(hook_json("post_edit") | changes), role="frontend", at=11)


def test_prompt_is_recorded_under_its_prompt_id(graph: Graph, hook_json: HookJson) -> None:
    ensure_schema(graph)
    _prompt(graph, hook_json, prompt="Add the avatar")
    rows = graph.query(
        "MATCH (:Session {id: 's-test'})-[:RECEIVED]->(r:Request) RETURN r.id, r.text"
    )
    assert rows.result_set == [["p-test", "Add the avatar"]]


def test_edit_is_recorded_under_its_tool_use_id(graph: Graph, hook_json: HookJson) -> None:
    _prompt(graph, hook_json)
    _edit(graph, hook_json)
    rows = why_file(graph, "hello.txt")
    assert len(rows) == 1
    assert "+hello" in rows[0].edit_summary
    ids = graph.query("MATCH (e:Edit) RETURN e.id").result_set
    assert ids == [["t-edit"]]


def test_edit_without_prompt_id_attaches_to_latest_request(
    graph: Graph, hook_json: HookJson
) -> None:
    _prompt(graph, hook_json)
    data = hook_json("post_edit")
    del data["prompt_id"]
    on_post_tool_use(graph, _hook(data), role="frontend", at=11)
    assert len(why_file(graph, "hello.txt")) == 1


def test_edit_whose_prompt_was_never_recorded_attaches_to_latest_request(
    graph: Graph, hook_json: HookJson
) -> None:
    _prompt(graph, hook_json)
    _edit(graph, hook_json, prompt_id="p-unknown")
    assert len(why_file(graph, "hello.txt")) == 1


def test_edit_before_any_prompt_records_nothing_and_does_not_fail(
    graph: Graph, hook_json: HookJson
) -> None:
    _edit(graph, hook_json)
    assert graph.query("MATCH (e:Edit) RETURN count(e)").result_set == [[0]]
    assert graph.query("MATCH (s:Session) RETURN s.role").result_set == [["frontend"]]


def test_tools_that_do_not_edit_record_nothing(graph: Graph, hook_json: HookJson) -> None:
    _prompt(graph, hook_json)
    data = hook_json("post_edit") | {"tool_name": "Read", "tool_input": {"file_path": "/x"}}
    on_post_tool_use(graph, _hook(data), role="frontend", at=11)
    assert graph.query("MATCH (e:Edit) RETURN count(e)").result_set == [[0]]


def test_second_prompt_in_session_follows_the_first(graph: Graph, hook_json: HookJson) -> None:
    _prompt(graph, hook_json)
    _prompt(graph, hook_json, prompt_id="p-second", prompt="next")
    assert latest_request_id(graph, "s-test") == "p-second"
