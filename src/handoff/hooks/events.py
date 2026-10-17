"""What each hook event records in the graph. Input is already prepared and redacted."""

from __future__ import annotations

from typing import Any

from falkordb import Graph

from handoff.graph.edits import add_edit
from handoff.graph.requests import (
    add_request,
    last_request_at,
    latest_request_id,
    request_needs_decision,
    request_text,
)
from handoff.graph.sessions import upsert_session
from handoff.hooks.delivery import (
    collision_text,
    conventions_text,
    open_needs_text,
    pending_messages_text,
)
from handoff.hooks.hook_input import HookInput
from handoff.ids import new_id


def register_session(graph: Graph, hook: HookInput, *, role: str, at: int) -> None:
    """Every event registers its session: SessionStart does not always fire."""
    upsert_session(graph, session_id=hook.session_id, role=role, cwd=hook.cwd, at=at, pid=hook.pid)


RESUMED = frozenset({"resume", "compact", "clear"})  # starts that lose what the session knew


def on_session_start(
    graph: Graph, hook: HookInput, *, role: str, at: int, live: bool = True
) -> str:
    """Register the session. A session that was resumed, cleared or compacted has forgotten
    the standing rules and open needs it was told, so it hears them again."""
    register_session(graph, hook, role=role, at=at)
    if not live or hook.source not in RESUMED:
        return ""
    parts = [conventions_text(graph, role), open_needs_text(graph, role)]
    return "\n".join(p for p in parts if p)


_WAKE_UP_PREFIX = "<task-notification>"


def is_wake_up(prompt: str) -> bool:
    """True for the turn Claude Code starts when our waiter wakes a session: it carries a
    delivered message, not new work from the person, so it is not a new request."""
    return prompt.lstrip().startswith(_WAKE_UP_PREFIX)


def _rules_to_hear(graph: Graph, role: str, seq: int, last_request: int | None) -> str:
    """All the standing rules on a session's first request; after that only the rules made
    since its previous request (so a rule added mid-session still reaches it, once)."""
    if seq == 1:
        return conventions_text(graph, role)
    if seq > 1 and last_request is not None:
        return conventions_text(graph, role, since=last_request)
    return ""


def on_user_prompt(graph: Graph, hook: HookInput, *, role: str, at: int, live: bool = True) -> str:
    """Record the prompt as a request. Returns text to add to Claude's context."""
    register_session(graph, hook, role=role, at=at)  # also creates the graph on first use
    last_request = last_request_at(graph, hook.session_id)  # before this prompt is recorded
    seq = 0
    if not is_wake_up(hook.prompt):
        seq = add_request(
            graph,
            session_id=hook.session_id,
            request_id=hook.prompt_id or new_id(),
            text=hook.prompt,
            at=at,
        )
    if not live:
        return ""
    parts = [
        _rules_to_hear(graph, role, seq, last_request),
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
    parts = [pending_messages_text(graph, session_id=hook.session_id, role=role, at=at)]
    if hook.edit_path is not None:
        parts.append(
            collision_text(
                graph, path=hook.edit_path, session_id=hook.session_id, at=at, pid=hook.pid
            )
        )
    text = "\n".join(p for p in parts if p)
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
