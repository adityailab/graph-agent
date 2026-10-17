from __future__ import annotations

from collections.abc import Callable
from typing import Any

from falkordb import Graph

from handoff.graph.messages import add_message
from handoff.graph.needs import add_need
from handoff.graph.requests import add_request
from handoff.graph.schema import ensure_schema
from handoff.graph.sessions import upsert_session
from handoff.hooks.dispatch import apply_event
from handoff.hooks.prepare import prepare_hook_input

HookJson = Callable[[str], dict[str, Any]]


def _apply(graph: Graph, raw: dict[str, Any], *, live: bool = True) -> Any:
    event = {"input": prepare_hook_input(raw, "/work/app"), "role": "frontend", "at": 100}
    return apply_event(graph, event, live=live)


def _backend_says(graph: Graph, text: str) -> None:
    ensure_schema(graph)
    upsert_session(graph, session_id="be", role="backend", cwd="/work/app", at=50)
    add_message(
        graph,
        message_id="m1",
        from_session_id="be",
        to_role="frontend",
        kind="message",
        text=text,
        reply_to=None,
        at=60,
    )


def test_next_prompt_carries_pending_messages(graph: Graph, hook_json: HookJson) -> None:
    _backend_says(graph, "avatarUrl is live")
    output = _apply(graph, hook_json("user_prompt"))
    assert "from the backend session" in output
    assert '"avatarUrl is live"' in output
    assert "avatarUrl is live" not in (_apply(graph, hook_json("user_prompt")) or "")


def test_tool_calls_carry_pending_messages(graph: Graph, hook_json: HookJson) -> None:
    _apply(graph, hook_json("user_prompt"))
    _backend_says(graph, "avatarUrl is live")
    output = _apply(graph, hook_json("post_edit"))
    assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "avatarUrl is live" in output["hookSpecificOutput"]["additionalContext"]


def test_replayed_events_never_deliver(graph: Graph, hook_json: HookJson) -> None:
    _backend_says(graph, "avatarUrl is live")
    assert _apply(graph, hook_json("user_prompt"), live=False) in ("", None)
    assert "avatarUrl is live" in _apply(graph, hook_json("user_prompt") | {"prompt_id": "p2"})


def test_prompt_mentions_open_needs_for_this_role(graph: Graph, hook_json: HookJson) -> None:
    _backend_says(graph, "hi")
    add_request(graph, session_id="be", request_id="pb", text="api", at=55)
    add_need(
        graph, request_id="pb", need_id="n1", text="show the new field", for_role="frontend", at=56
    )
    assert "1 open need is addressed to frontend" in _apply(graph, hook_json("user_prompt"))


def test_editing_a_file_another_session_just_changed_is_flagged(
    graph: Graph, hook_json: HookJson
) -> None:
    from handoff.graph.edits import add_edit

    _backend_says(graph, "hi")
    add_request(graph, session_id="be", request_id="pb", text="rename the field", at=90)
    add_edit(graph, request_id="pb", edit_id="eb", tool="Edit", path="hello.txt", summary="", at=95)
    _apply(graph, hook_json("user_prompt"))
    output = _apply(graph, hook_json("post_edit"))
    context = output["hookSpecificOutput"]["additionalContext"]
    assert "hello.txt was also changed by the backend session" in context
    assert '"rename the field"' in context


def test_open_needs_are_listed_with_their_ids_and_who_raised_them(
    graph: Graph, hook_json: HookJson
) -> None:
    _backend_says(graph, "hi")
    add_request(graph, session_id="be", request_id="pb", text="api", at=55)
    add_need(
        graph, request_id="pb", need_id="n1", text="show the new field", for_role="frontend", at=56
    )
    text = _apply(graph, hook_json("user_prompt"))
    assert "need n1 from backend: show the new field" in text
    assert "resolve_need" in text
