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


_TOOL_STEPS = {
    "graph_guide": "reading the graph guide",
    "get_graph_schema": "reading the graph schema",
    "list_graphs": "listing the graphs",
    "handoff": "reading the handoff",
    "search": "searching decisions",
    "why": "tracing why a file changed",
}
_SHOWN = 120  # characters of a query or search shown in a step


def _tool_step(call: ToolCall) -> str | None:
    short = call.name.rsplit("__", 1)[-1]
    if short == "query_graph_readonly":
        return "running Cypher: " + " ".join(str(call.input.get("query", "")).split())[:_SHOWN]
    step = _TOOL_STEPS.get(short)
    detail = str(call.input.get("query") or call.input.get("path") or "")
    return f"{step}: {detail[:_SHOWN]}" if step and detail else step


def step_labels(event: dict[str, Any]) -> list[str]:
    """Plain-language steps one stream event shows (thinking, a tool being used, the answer
    being written), in order. Tools that are only the harness looking things up show nothing."""
    kind = event.get("type")
    if kind == "system" and event.get("subtype") == "init":
        return ["starting Claude Code"]
    if kind != "assistant":
        return []
    steps: list[str | None] = []
    for block in event.get("message", {}).get("content", []):
        if not isinstance(block, dict):
            continue
        if block.get("type") == "thinking":
            steps.append("thinking")
        elif block.get("type") == "tool_use":
            steps.append(_tool_step(ToolCall(str(block.get("name", "")), block.get("input") or {})))
        elif block.get("type") == "text":
            steps.append("writing the answer")
    return [s for s in steps if s]


def delta_of(event: dict[str, Any]) -> tuple[str, str] | None:
    """("text" | "thought", words) for a partial-message event, so they can be shown as they
    are written; None for every other event."""
    if event.get("type") != "stream_event":
        return None
    inner = event.get("event", {})
    delta = inner.get("delta", {}) if inner.get("type") == "content_block_delta" else {}
    if delta.get("type") == "text_delta":
        return "text", str(delta.get("text", ""))
    if delta.get("type") == "thinking_delta":
        return "thought", str(delta.get("thinking", ""))
    return None
