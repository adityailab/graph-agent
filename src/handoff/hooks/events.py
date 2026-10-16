"""What each hook event records in the graph. Input is already prepared and redacted."""

from __future__ import annotations

from typing import Any

from falkordb import Graph

from handoff.graph.edits import add_edit
from handoff.graph.requests import (
    add_request,
    latest_request_id,
    request_needs_decision,
    request_text,
)
from handoff.graph.sessions import upsert_session
from handoff.hooks.delivery import open_needs_text, pending_messages_text
from handoff.hooks.hook_input import HookInput
from handoff.ids import new_id


def register_session(graph: Graph, hook: HookInput, *, role: str, at: int) -> None:
    """Every event registers its session: SessionStart does not always fire."""
    upsert_session(graph, session_id=hook.session_id, role=role, cwd=hook.cwd, at=at)


def on_session_start(graph: Graph, hook: HookInput, *, role: str, at: int) -> None:
    """Register the session."""
    register_session(graph, hook, role=role, at=at)


def on_user_prompt(graph: Graph, hook: HookInput, *, role: str, at: int, live: bool = True) -> str:
    """Record the prompt as a request. Returns text to add to Claude's context."""
    register_session(graph, hook, role=role, at=at)
    add_request(
        graph,
        session_id=hook.session_id,
        request_id=hook.prompt_id or new_id(),
        text=hook.prompt,
        at=at,
    )
    if not live:
        return ""
    parts = [
        pending_messages_text(graph, session_id=hook.session_id, role=role, at=at),
        open_needs_text(graph, role),
    ]
    return "\n".join(p for p in parts if p)


def on_post_tool_use(
    graph: Graph, hook: HookInput, *, role: str, at: int, live: bool = True
) -> dict[str, Any] | None:
    """Record a file edit, if any, then hand pending messages to the working session."""
    register_session(graph, hook, role=role, at=at)
    if hook.edit_path is not None:
        _record_edit(graph, hook, hook.edit_path, at)
    if not live:
        return None
    text = pending_messages_text(graph, session_id=hook.session_id, role=role, at=at)
    if not text:
        return None
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}


def _record_edit(graph: Graph, hook: HookInput, path: str, at: int) -> None:

    def record(request_id: str) -> bool:
        return add_edit(
            graph,
            request_id=request_id,
            edit_id=hook.tool_use_id,
            tool=hook.tool_name,
            path=path,
            summary=hook.edit_summary,
            at=at,
        )

    # The prompt may be unrecorded (hooks installed mid-turn); fall back to the latest one.
    if hook.prompt_id and record(hook.prompt_id):
        return
    latest = latest_request_id(graph, hook.session_id)
    if latest is not None:
        record(latest)


FINISH_CHECK_REASON = (
    "This request changed files but no decision is recorded for it yet. Other sessions "
    "learn why these files changed only from record_decision."
)


def on_stop(graph: Graph, hook: HookInput, *, role: str, at: int) -> dict[str, Any] | None:
    """The finish check: block the stop once if edits were made with no decision."""
    register_session(graph, hook, role=role, at=at)
    if hook.stop_hook_active:
        return None
    request_id = _turn_request_id(graph, hook)
    if request_id is None or not request_needs_decision(graph, request_id):
        return None
    return {"decision": "block", "reason": FINISH_CHECK_REASON}


def _turn_request_id(graph: Graph, hook: HookInput) -> str | None:
    """The request this turn worked on: its prompt if recorded, else the latest one,
    the same fallback edits use."""
    if hook.prompt_id and request_text(graph, hook.prompt_id) is not None:
        return hook.prompt_id
    return latest_request_id(graph, hook.session_id)
