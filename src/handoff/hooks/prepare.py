"""Reducing raw hook input to the small, redacted event that is stored or saved.

This runs the moment a hook fires, so nothing unredacted ever reaches the replay
file, and every id is fixed before the event can be replayed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from handoff.hooks.edits import edited_path, summarise
from handoff.ids import new_id
from handoff.paths import relative_path
from handoff.redact import redact

EDIT_TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})
MAX_PROMPT_CHARS = 20_000
_TEXT_FIELDS = ("old_string", "new_string", "content", "new_source")


def _edit_fields(tool_name: str, tool_input: Mapping[str, Any], project_dir: str) -> dict[str, Any]:
    path = edited_path(tool_input) if tool_name in EDIT_TOOLS else None
    if path is None:
        return {"edit_path": None, "edit_summary": ""}
    # Redact the full text before summarise() trims it, so a cut can't split a secret.
    cleaned = {k: redact(str(v)) if k in _TEXT_FIELDS else v for k, v in tool_input.items()}
    return {
        "edit_path": relative_path(path, project_dir),
        "edit_summary": summarise(tool_name, cleaned),
    }


def prepare_hook_input(data: Mapping[str, Any], project_dir: str) -> dict[str, Any]:
    """Return only the fields the handlers use, redacted, capped and with ids filled in."""
    tool_name = str(data.get("tool_name", ""))
    tool_input = data.get("tool_input")
    prepared: dict[str, Any] = {
        "hook_event_name": data.get("hook_event_name"),
        "session_id": data.get("session_id"),
        "cwd": str(data.get("cwd", "")),
        "prompt_id": data.get("prompt_id") or None,
        "prompt": redact(str(data.get("prompt", "")))[:MAX_PROMPT_CHARS],
        "tool_name": tool_name,
        "tool_use_id": data.get("tool_use_id") or new_id(),
        "stop_hook_active": bool(data.get("stop_hook_active", False)),
        "source": str(data.get("source", "")),
    }
    if prepared["hook_event_name"] == "UserPromptSubmit" and not prepared["prompt_id"]:
        prepared["prompt_id"] = new_id()
    tool_input = tool_input if isinstance(tool_input, Mapping) else {}
    return prepared | _edit_fields(tool_name, tool_input, project_dir)
