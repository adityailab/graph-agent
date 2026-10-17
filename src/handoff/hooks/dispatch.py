"""Routing a saved hook event to the handler for its event name."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from falkordb import Graph

from handoff.hooks.events import on_post_tool_use, on_session_start, on_stop, on_user_prompt
from handoff.hooks.hook_input import parse_hook_input

HookOutput = str | dict[str, Any] | None


def apply_event(graph: Graph, event: Mapping[str, Any], *, live: bool) -> HookOutput:
    """Apply one event: {"input": prepared hook input, "role", "at"}.

    The same shape is saved to the replay file, so live and replayed events take
    one path. A replayed event (`live=False`) only records: its output goes nowhere,
    so it must not deliver messages or block a stop. Returns what to print, if anything.
    """
    hook = parse_hook_input(event["input"])
    role, at = str(event["role"]), int(event["at"])
    if hook.event_name == "SessionStart":
        return on_session_start(graph, hook, role=role, at=at, live=live) or None
    if hook.event_name == "UserPromptSubmit":
        return on_user_prompt(graph, hook, role=role, at=at, live=live)
    if hook.event_name == "PostToolUse":
        return on_post_tool_use(graph, hook, role=role, at=at, live=live)
    if hook.event_name == "Stop":
        output = on_stop(graph, hook, role=role, at=at)
        return output if live else None
    return None
