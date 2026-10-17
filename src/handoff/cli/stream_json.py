"""Reading `claude -p --output-format stream-json --verbose`: the answer and the tools used."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    name: str
    input: dict[str, Any] = field(default_factory=dict)


def _tool_calls(event: dict[str, Any]) -> list[tuple[str, ToolCall]]:
    """(tool_use id, call) for each tool use in an assistant message."""
    content = event.get("message", {}).get("content", [])
    return [
        (str(c.get("id", "")), ToolCall(str(c.get("name", "")), c.get("input") or {}))
        for c in content
        if isinstance(c, dict) and c.get("type") == "tool_use"
    ]


def parse_stream(lines: Iterable[str]) -> tuple[str, list[ToolCall]]:
    """The final answer text and every tool call, in order. Unreadable lines are skipped."""
    answer, calls = "", []
    seen: set[str] = set()  # the stream can repeat a message; each tool use counts once
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "assistant":
            for use_id, call in _tool_calls(event):
                if not use_id or use_id not in seen:
                    seen.add(use_id)
                    calls.append(call)
        elif event.get("type") == "result":
            answer = str(event.get("result") or "")
    return answer.strip(), calls
