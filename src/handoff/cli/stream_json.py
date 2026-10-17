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


def _tool_calls(event: dict[str, Any]) -> list[ToolCall]:
    content = event.get("message", {}).get("content", [])
    return [
        ToolCall(str(c.get("name", "")), c.get("input") or {})
        for c in content
        if isinstance(c, list | dict) and isinstance(c, dict) and c.get("type") == "tool_use"
    ]


def parse_stream(lines: Iterable[str]) -> tuple[str, list[ToolCall]]:
    """The final answer text and every tool call, in order. Unreadable lines are skipped."""
    answer, calls = "", []
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "assistant":
            calls.extend(_tool_calls(event))
        elif event.get("type") == "result":
            answer = str(event.get("result") or "")
    return answer.strip(), calls
