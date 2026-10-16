"""The prepared hook event the handlers read (see hooks/prepare.py)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HookInput:
    """The fields of a prepared hook event."""

    event_name: str
    session_id: str
    cwd: str
    prompt_id: str | None = None
    prompt: str = ""
    tool_name: str = ""
    tool_use_id: str = ""
    edit_path: str | None = None
    edit_summary: str = ""
    stop_hook_active: bool = False


def parse_hook_input(data: Mapping[str, Any]) -> HookInput:
    """Build a HookInput; raises ValueError if the event name or session id is missing."""
    event_name = data.get("hook_event_name")
    session_id = data.get("session_id")
    if not event_name or not session_id:
        raise ValueError("hook input has no hook_event_name or session_id")
    edit_path = data.get("edit_path")
    return HookInput(
        event_name=str(event_name),
        session_id=str(session_id),
        cwd=str(data.get("cwd", "")),
        prompt_id=str(data["prompt_id"]) if data.get("prompt_id") else None,
        prompt=str(data.get("prompt", "")),
        tool_name=str(data.get("tool_name", "")),
        tool_use_id=str(data.get("tool_use_id", "")),
        edit_path=str(edit_path) if edit_path else None,
        edit_summary=str(data.get("edit_summary", "")),
        stop_hook_active=bool(data.get("stop_hook_active", False)),
    )
