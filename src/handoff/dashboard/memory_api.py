"""The memory endpoints: one kind of memory opened into its items, and relevant memories."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any
from urllib.parse import unquote

from handoff.config import Config
from handoff.graph.connection import connect, graph_exists
from handoff.graph.context_view import GraphView
from handoff.graph.memory_graph import memory_graph
from handoff.graph.memory_items import MemoryItem, memory_items, relevant_memories
from handoff.graph.memory_view import role_contexts

PREFIX = "/api/memory/"
LIMIT = 60
RELEVANT = 8
GRAPH_EDGES = 150


def _drawing(view: GraphView) -> dict[str, Any]:
    return {"nodes": [asdict(n) for n in view.nodes], "edges": [asdict(e) for e in view.edges]}


def _payload(items: list[MemoryItem]) -> dict[str, Any]:
    return {"items": [asdict(i) for i in items]}


def memory_response(
    config: Config, path: str, *, now: int, window_ms: int
) -> dict[str, Any] | None:
    """JSON for `/api/memory/<kind>` or `/api/memory/relevant/<role>`; None when the path names
    nothing (the server then answers 404)."""
    name = unquote(path.removeprefix(PREFIX))
    kinds = ("working", "episodic", "semantic", "procedural", "temporal", "social")
    relevant = name.startswith("relevant/")
    drawn = name.endswith("/graph") and name.removesuffix("/graph") in kinds
    if not relevant and not drawn and name not in kinds:
        return None
    if not graph_exists(config):
        return {"nodes": [], "edges": []} if drawn else _payload([])
    graph, since = connect(config), now - window_ms
    if drawn:
        return _drawing(memory_graph(graph, name.removesuffix("/graph"), limit=GRAPH_EDGES))
    if not relevant:
        return _payload(
            memory_items(graph, name, since=since, limit=LIMIT, oldest_first=name == "temporal")
        )
    role = name.removeprefix("relevant/")
    task = next((c.working_on for c in role_contexts(graph, since=since) if c.role == role), "")
    return _payload(relevant_memories(graph, task, k=RELEVANT))
