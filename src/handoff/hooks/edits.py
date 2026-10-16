"""Turning a file-edit tool call into a path and a short summary."""

from __future__ import annotations

import difflib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

MAX_SUMMARY_LINES = 40
MAX_SUMMARY_CHARS = 4000


def edited_path(tool_input: Mapping[str, Any]) -> str | None:
    """Return the file an edit tool changed, if its input names one."""
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    return str(path) if path else None


def relative_path(file_path: str, project_dir: str) -> str:
    """Return the path relative to the project, or unchanged if it lies outside it."""
    path, root = Path(file_path), Path(project_dir)
    return str(path.relative_to(root)) if path.is_relative_to(root) else file_path


def _cap(lines: list[str]) -> str:
    shown = lines[:MAX_SUMMARY_LINES]
    text = "\n".join(shown)[:MAX_SUMMARY_CHARS]
    hidden = len(lines) - len(shown)
    return f"{text}\n… {hidden} more lines" if hidden > 0 else text


def summarise(tool_name: str, tool_input: Mapping[str, Any]) -> str:
    """Return a short, capped description of what an edit tool changed."""
    if tool_name == "Edit":
        old = str(tool_input.get("old_string", "")).splitlines()
        new = str(tool_input.get("new_string", "")).splitlines()
        diff = difflib.unified_diff(old, new, lineterm="", n=1)
        return _cap([line for line in diff if not line.startswith(("---", "+++"))])
    if tool_name == "Write":
        lines = str(tool_input.get("content", "")).splitlines()
        return _cap([f"wrote {len(lines)} lines", *lines])
    if tool_name == "NotebookEdit":
        mode = tool_input.get("edit_mode") or "replace"
        lines = str(tool_input.get("new_source", "")).splitlines()
        return _cap([f"{mode} cell {tool_input.get('cell_id', '?')}", *lines])
    return tool_name
