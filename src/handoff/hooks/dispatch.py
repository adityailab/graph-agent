"""Routing a saved hook event to the handler for its event name."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from falkordb import Graph

from handoff.hooks.events import on_post_tool_use, on_session_start, on_user_prompt
from handoff.hooks.hook_input import parse_hook_input

HookOutput = str | dict[str, Any] | None


def apply_event(graph: Graph, event: Mapping[str, Any]) -> HookOutput:
    """Apply one event: {"input": hook JSON, "role", "project_dir", "at"}.

    The same shape is saved to the replay file, so live and replayed events take
    one path. Returns what the hook should print, if anything.
    """
    hook = parse_hook_input(event["input"])
    role, at = str(event["role"]), int(event["at"])
    if hook.event_name == "SessionStart":
        on_session_start(graph, hook, role=role, at=at)
        return None
    if hook.event_name == "UserPromptSubmit":
        return on_user_prompt(graph, hook, role=role, at=at)
    if hook.event_name == "PostToolUse":
        project_dir = str(event["project_dir"])
        return on_post_tool_use(graph, hook, role=role, project_dir=project_dir, at=at)
    return None
