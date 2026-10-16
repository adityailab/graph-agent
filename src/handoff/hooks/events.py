"""What each hook event records in the graph. Input is already prepared and redacted."""

from __future__ import annotations

from typing import Any

from falkordb import Graph

from handoff.graph.edits import add_edit
from handoff.graph.requests import add_request, latest_request_id
from handoff.graph.sessions import upsert_session
from handoff.hooks.hook_input import HookInput
from handoff.ids import new_id


def register_session(graph: Graph, hook: HookInput, *, role: str, at: int) -> None:
    """Every event registers its session: SessionStart does not always fire."""
    upsert_session(graph, session_id=hook.session_id, role=role, cwd=hook.cwd, at=at)


def on_session_start(graph: Graph, hook: HookInput, *, role: str, at: int) -> None:
    """Register the session."""
    register_session(graph, hook, role=role, at=at)


def on_user_prompt(graph: Graph, hook: HookInput, *, role: str, at: int) -> str:
    """Record the prompt as a request. Returns text to add to Claude's context."""
    register_session(graph, hook, role=role, at=at)
    add_request(
        graph,
        session_id=hook.session_id,
        request_id=hook.prompt_id or new_id(),
        text=hook.prompt,
        at=at,
    )
    return ""


def on_post_tool_use(graph: Graph, hook: HookInput, *, role: str, at: int) -> dict[str, Any] | None:
    """Record a file edit against the request that caused it. Returns hook JSON output."""
    register_session(graph, hook, role=role, at=at)
    if hook.edit_path is None:
        return None
    path = hook.edit_path

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
        return None
    latest = latest_request_id(graph, hook.session_id)
    if latest is not None:
        record(latest)
    return None
